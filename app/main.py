"""RK3 web app: documents API, async conversion, static viewer + output.

Conversions run in a subprocess (python -m rk3 convert <slug>), not in-process:
a heavy or leaky conversion (pdfium bitmaps, PIL crops, large artifacts) must
not be able to OOM the web server.
"""

import datetime
import json
import re
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from rk3.ai import ai_can_analyze, ai_can_generate, ai_mode
from rk3.documents import OUTPUT, list_documents, output_dir, source_for_slug
from rk3.eval import (append_check, canonical_for_nid, checks_with_status,
                      evaluate_check)
from rk3.pipeline import build_status
from rk3.toccompare import compare as toc_compare
from rk3.landing.ai import (
    find_findings, find_intro_section, generate_landing_ai, generate_summary_variant)
from rk3.landing.extract import build_default_theme
from rk3.landing.templates import ARCHETYPE_LABELS, block_defaults, build_config

ROOT = Path(__file__).resolve().parent.parent
FEEDBACK = ROOT / "feedback"

app = FastAPI(title="RK3")

_active: set[str] = set()
# a save that lands WHILE a convert is running must not be dropped: the
# running convert already read the ops/config files and won't see it. Mark
# the slug dirty; when the convert finishes it immediately reruns once
# (fingerprints make the rerun cheap — render-only for op saves).
_rerun: set[str] = set()
_active_lock = threading.Lock()


@app.get("/api/documents")
def documents():
    docs = list_documents()
    with _active_lock:
        for d in docs:
            if d["slug"] in _active:
                d["status"] = "in_progress"
    return docs


def _clean_font(name: str) -> str:
    """'ANGKGH+Gotham-Book' -> 'Gotham-Book' (drop the subset tag)."""
    return re.sub(r"^[A-Z]{6}\+", "", name or "")


@app.get("/api/pdf-metadata")
def pdf_metadata():
    """Admin → PDF Metadata: one row per document with its authoring tools
    (PDF Creator/Producer) and the fonts it uses, ranked by how much text each
    sets. The main (bulk) font is surfaced; the long tail stays collapsed so a
    document with dozens of named fonts can't blow up the table.

    Authoring tool is read straight from the PDF (every doc has one); font usage
    comes from the converted ir.json (so it's blank until a doc is converted)."""
    import pypdfium2 as pdfium

    rows = []
    for d in list_documents():
        slug = d["slug"]
        row = {"slug": slug, "docName": d["name"], "folder": d.get("folder"),
               "creator": None, "producer": None,
               "mainFont": None, "fontCount": 0, "fonts": [],
               # embed verdict: True=fully reconstructable (default on),
               # False=some font drops glyphs (default off), None=no embeddable
               "embedComplete": None, "embedTotal": 0, "embedPartial": 0,
               # tagging verdict: full/partial/none usable struct-tree order
               "tagged": None, "taggedPages": 0, "taggedTotal": 0}
        src = source_for_slug(slug)
        if src is not None:
            try:
                pdf = pdfium.PdfDocument(str(src))
                meta = pdf.get_metadata_dict()
                row["creator"] = (meta.get("Creator") or "").strip() or None
                row["producer"] = (meta.get("Producer") or "").strip() or None
                pdf.close()
            except Exception:
                pass
        ir_path = output_dir(slug) / "ir.json"
        if ir_path.exists():
            try:
                ir = json.loads(ir_path.read_text())
                usage: Dict[str, int] = {}
                embedded = {_clean_font(k) for k in (ir.get("fonts_embed") or {})}

                def feed(n):
                    f = (n.get("data") or {}).get("font")
                    t = len(n.get("text") or "")
                    if f and t:
                        usage[_clean_font(f)] = usage.get(_clean_font(f), 0) + t

                for n in ir.get("body", []):
                    feed(n)
                    for c in n.get("children", []):
                        feed(c)
                ranked = sorted(usage.items(), key=lambda kv: -kv[1])
                if ranked:
                    row["mainFont"] = ranked[0][0]
                    row["fontCount"] = len(ranked)
                    row["fonts"] = [{"name": nm, "chars": c,
                                     "embedded": nm in embedded}
                                    for nm, c in ranked]
                fe = ir.get("fonts_embed") or {}
                row["embedTotal"] = len(fe)
                row["embedPartial"] = sum(
                    1 for e in fe.values() if not e.get("complete", True))
                row["embedComplete"] = bool(ir.get("fonts_complete")) if fe else None
                tg = ir.get("tagged") or {}
                row["tagged"] = tg.get("verdict")
                row["taggedPages"] = tg.get("structPages", 0)
                row["taggedTotal"] = tg.get("totalPages", 0)
            except Exception:
                pass
        rows.append(row)
    return rows


class Assertion(BaseModel):
    """One eval check authored from the review UI — exactly the shape eval/<slug>
    .yaml stores. Exactly one of order/role/list/merge is set. `items` carries
    the JSON key `list` (which collides with the builtin as a field name)."""
    model_config = {"populate_by_name": True}
    note: Optional[str] = None
    stage: Optional[str] = None
    order: Optional[List[str]] = None
    role: Optional[Dict] = None
    items: Optional[List[str]] = Field(default=None, alias="list")
    merge: Optional[List[str]] = None
    ordered: Optional[str] = None
    freeze: Optional[Dict] = None


def _assertion_check(a: Assertion) -> dict:
    # drop empties so the stored check is the minimal {kind: ...,(stage),(note)},
    # restoring the wire key `list` for the items field
    return {k: v for k, v in a.model_dump(by_alias=True).items()
            if v not in (None, [], "")}


@app.get("/api/assertions/{slug}")
def list_assertions(slug: str, response: Response):
    """All eval checks on the doc, each evaluated live against the current
    artifacts + resolved to its anchoring nid — backs the ⚑ markers."""
    response.headers["Cache-Control"] = "no-store"
    if source_for_slug(slug) is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    return {"checks": checks_with_status(slug)}


_STAKE_PAGE = re.compile(r"\bp(\d{1,4})\b")


@app.get("/api/stakes/{slug}")
def get_stakes(slug: str, response: Response):
    """Every gold stake on the doc, evaluated live against the current
    artifacts (green/red) with its anchoring nid + a page hint — backs the
    Stakes tab (webified §1.3). Thin wrapper over rk3.eval.checks_with_status
    so the tab and `python -m rk3 eval` agree exactly."""
    response.headers["Cache-Control"] = "no-store"
    if source_for_slug(slug) is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    checks = checks_with_status(slug)
    for c in checks:
        m = _STAKE_PAGE.search(c.get("note") or "")
        c["page"] = int(m.group(1)) if m else None
    green = sum(1 for c in checks if c.get("ok"))
    return {"slug": slug, "green": green, "red": len(checks) - green, "checks": checks}


@app.get("/api/scoreboard/{slug}")
def get_scoreboard(slug: str, response: Response):
    """Live per-page scoreboard for the owner QA-surface gallery (webified §1.5a):
    one record per page {class, scanned, visionIssues, stakes, openOwnerNotes}.
    Computed fresh (triage + live stakes + feedback + the scanned-crop signal) so
    the gallery's status rings reflect the current artifacts, not a stale snapshot."""
    response.headers["Cache-Control"] = "no-store"
    if source_for_slug(slug) is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    from tools.scoreboard import build as build_scoreboard
    board = build_scoreboard(slug)
    if board is None:
        raise HTTPException(404, "no ir.json — convert the document first")
    return board


@app.get("/api/assertions/{slug}/snapshot")
def assertion_snapshot(slug: str, nid: str, response: Response):
    """The semantic content to freeze for one element — text + em/strong/a +
    list/heading structure, with data-*/CSS stripped. Backs the 'freeze this'
    preview in the review UI."""
    response.headers["Cache-Control"] = "no-store"
    res = canonical_for_nid(slug, nid)
    if res is None:
        raise HTTPException(404, f"no element {nid!r} in {slug!r}")
    anchor, html = res
    return {"anchor": anchor, "html": html}


@app.post("/api/assertions/{slug}/validate")
def validate_assertion(slug: str, a: Assertion):
    if source_for_slug(slug) is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    try:
        ok, detail = evaluate_check(slug, _assertion_check(a))
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"ok": ok, "detail": detail}


@app.post("/api/assertions/{slug}")
def save_assertion(slug: str, a: Assertion, force: bool = False):
    """Validate, then save to eval/<slug>.yaml. A passing assertion always
    saves; a failing one saves only with force=true (intentional regression
    target)."""
    if source_for_slug(slug) is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    check = _assertion_check(a)
    try:
        ok, detail = evaluate_check(slug, check)
    except ValueError as e:
        raise HTTPException(422, str(e))
    saved = False
    total = None
    if ok or force:
        total = append_check(slug, check)
        saved = True
    return {"ok": ok, "detail": detail, "saved": saved, "total": total}


@app.get("/api/build-status/{slug}")
def get_build_status(slug: str, response: Response):
    # never cache: this is the signal the UI uses to know whether the doc (and
    # the iframe it's about to bust) is the latest
    response.headers["Cache-Control"] = "no-store"
    return build_status(slug)


@app.get("/api/toc-compare/{slug}")
def get_toc_compare(slug: str):
    """Read-only TOC ⇔ headings reconciliation (diagnostic; writes nothing)."""
    try:
        return toc_compare(slug)
    except FileNotFoundError:
        raise HTTPException(404, "no output for this document")


@app.post("/api/convert/{slug}")
def start_convert(slug: str, force: bool = False):
    if source_for_slug(slug) is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    _spawn_convert(slug, force)
    return {"slug": slug, "status": "in_progress"}


class DocConfig(BaseModel):
    # null clears the override -> revert to "auto" (embed iff fully covered)
    embedFonts: Optional[bool] = None


@app.post("/api/doc-config/{slug}")
def set_doc_config(slug: str, cfg: DocConfig):
    """Persist a per-document setting to <name>.config.json (next to the PDF) so
    the user's embed choice survives reconversions. Then re-render so the output
    reflects it. embedFonts=null removes the override (back to auto-detect)."""
    src = source_for_slug(slug)
    if src is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    cfg_path = src.with_suffix("").with_name(src.stem + ".config.json")
    data = {}
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text())
        except json.JSONDecodeError:
            data = {}
    out = data.setdefault("output", {})
    if cfg.embedFonts is None:
        out.pop("embedFonts", None)
        if not out:
            data.pop("output", None)
    else:
        out["embedFonts"] = cfg.embedFonts
    cfg_path.write_text(json.dumps(data, indent=2) + "\n")
    _spawn_convert(slug, force=False)  # render-only: embedFonts is a render dep
    return {"ok": True, "embedFonts": cfg.embedFonts}


def _spawn_convert(slug: str, force: bool = False):
    with _active_lock:
        if slug in _active:
            # coalesce, don't drop: the user saved again mid-convert (two
            # quick saves made tenure's and invest's newest merge "not take").
            # The finishing convert reruns once for everything that landed.
            _rerun.add(slug)
            return
        _active.add(slug)

    def work():
        # capture stdout+stderr to a per-doc log instead of /dev/null — a crash,
        # OOM-kill (exit 137/-9), or import error must be inspectable, not silent
        log_path = output_dir(slug) / "convert.log"
        try:
            cmd = [sys.executable, "-m", "rk3", "convert", slug]
            if force:
                cmd.append("--force")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            r = subprocess.run(cmd, cwd=ROOT, timeout=3600,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True)
            log_path.write_text(
                f"$ {' '.join(cmd)}\nexit={r.returncode}\n\n{r.stdout or ''}")
            if r.returncode != 0:
                _record_convert_crash(slug, r.returncode, r.stdout or "")
        except Exception as e:  # the subprocess itself couldn't be launched/timed out
            log_path.write_text(f"convert spawn failed: {e!r}")
            _record_convert_crash(slug, -1, repr(e))
        finally:
            with _active_lock:
                _active.discard(slug)
                again = slug in _rerun
                _rerun.discard(slug)
            if again:
                _spawn_convert(slug)

    threading.Thread(target=work, daemon=True, name=f"convert-{slug}").start()


def _record_convert_crash(slug: str, returncode: int, output: str):
    """A non-zero subprocess exit (OOM-kill, import error, hard crash) may never
    reach the pipeline's own try/except — stamp meta.json so build-status shows
    'build failed' instead of a stale 'current'."""
    meta_path = output_dir(slug) / "meta.json"
    try:
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    except json.JSONDecodeError:
        meta = {}
    # don't clobber a richer traceback the pipeline already recorded
    if meta.get("status") != "failed":
        tail = "\n".join((output or "").strip().splitlines()[-25:])
        meta["status"] = "failed"
        meta["error"] = f"convert exited {returncode}\n{tail}" if tail \
            else f"convert exited {returncode} (no output; likely OOM-killed)"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, indent=2))


@app.get("/api/convert-log/{slug}")
def get_convert_log(slug: str, response: Response):
    response.headers["Cache-Control"] = "no-store"
    log_path = output_dir(slug) / "convert.log"
    if not log_path.exists():
        return {"slug": slug, "log": None}
    return {"slug": slug, "log": log_path.read_text()}


class FeedbackEntry(BaseModel):
    """One viewer annotation. Either an element target (nid/rk) or a PDF-pane
    spot (page + fractional coords). type: "comment" | "answer".
    Answers carry qid + choice. This same stream later feeds the in-codebase
    config agent; during development Claude reads it directly."""
    type: str = "comment"
    # reviewer-chosen category for a comment, so QA passes can be filtered:
    # structure | styling | figure | pattern
    category: str | None = None
    text: str = ""
    nid: str | None = None
    rk: str | None = None
    page: int | None = None
    xf: float | None = None
    yf: float | None = None
    qid: str | None = None
    choice: str | None = None
    # denormalized context captured at click time, so entries stay readable
    # even if the underlying nid/qid later drifts
    qKind: str | None = None
    qPrompt: str | None = None
    elementText: str | None = None
    # span-level targeting: selected text + char offsets within the node text
    selText: str | None = None
    selStart: int | None = None
    selEnd: int | None = None
    id: str | None = None  # present => update that entry instead of appending


def _feedback_path(slug: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        raise HTTPException(400, "bad slug")
    FEEDBACK.mkdir(exist_ok=True)
    return FEEDBACK / f"{slug}.jsonl"


@app.get("/api/feedback")
def get_all_feedback():
    """Every feedback entry across all documents, tagged with its doc slug/name,
    for the Admin → All Feedback table. Includes cleared entries (the client
    toggles 'show closed')."""
    names = {d["slug"]: d["name"] for d in list_documents()}
    out = []
    if FEEDBACK.is_dir():
        for path in sorted(FEEDBACK.glob("*.jsonl")):
            slug = path.stem
            for line in path.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rec["slug"] = slug
                rec["docName"] = names.get(slug, slug)
                out.append(rec)
    return out


@app.get("/api/feedback/{slug}")
def get_feedback(slug: str):
    path = _feedback_path(slug)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@app.post("/api/feedback/{slug}")
def post_feedback(slug: str, entry: FeedbackEntry):
    if source_for_slug(slug) is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    path = _feedback_path(slug)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    body = entry.model_dump(exclude_none=True)

    if entry.id:  # edit an existing entry in place
        lines = [json.loads(l) for l in path.read_text().splitlines()
                 if l.strip()] if path.exists() else []
        for i, rec in enumerate(lines):
            if rec.get("id") == entry.id:
                rec.update(body)
                rec["edited"] = now
                lines[i] = rec
                path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                        for r in lines))
                return rec
        raise HTTPException(404, f"no feedback entry {entry.id!r}")

    rec = {"ts": now, "status": "open", "id": str(uuid.uuid4())[:8], **body}
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


@app.post("/api/feedback/{slug}/{entry_id}/clear")
def clear_feedback(slug: str, entry_id: str):
    """Soft-delete: the user confirms a resolution and moves the note to
    trash. It stays in the jsonl (status: cleared) until the trash is emptied."""
    path = _feedback_path(slug)
    if not path.exists():
        raise HTTPException(404, "no feedback for document")
    lines = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    for rec in lines:
        if rec.get("id") == entry_id:
            rec["status"] = "cleared"
            rec["clearedAt"] = datetime.datetime.now(datetime.timezone.utc) \
                .isoformat(timespec="seconds")
            path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                    for r in lines))
            return rec
    raise HTTPException(404, f"no feedback entry {entry_id!r}")


class QaRunBody(BaseModel):
    pages: List[int] | None = None   # None = all pages (costly)


class DispositionBody(BaseModel):
    disposition: str                 # open | fixed | accepted | dismissed
    note: str | None = None


@app.post("/api/qa/{slug}/run")
def run_vision_qa(slug: str, body: QaRunBody):
    """Run the vision-QA reviewer and append its flags to the feedback queue as
    triageable issues (source=vision-qa, severity, kind, disposition=open).
    De-duplicates against still-open vision-QA issues so re-runs don't flood."""
    from rk3.visionqa import qa_doc
    flags = qa_doc(slug, pages=body.pages)
    path = _feedback_path(slug)
    existing = ([json.loads(l) for l in path.read_text().splitlines() if l.strip()]
                if path.exists() else [])
    open_keys = {(e.get("page"), e.get("text")) for e in existing
                 if e.get("source") == "vision-qa"
                 and e.get("disposition", "open") == "open"}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    added = []
    with path.open("a") as fh:
        for f in flags:
            key = (f.get("page"), f.get("issue"))
            if key in open_keys:
                continue
            rec = {"ts": now, "id": str(uuid.uuid4())[:8], "status": "open",
                   "disposition": "open", "type": "issue", "source": "vision-qa",
                   "severity": f.get("severity"), "kind": f.get("kind", "error"),
                   "category": f.get("category"), "text": f.get("issue", ""),
                   "where": f.get("where"), "fix": f.get("fix"), "page": f.get("page")}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            added.append(rec)
            open_keys.add(key)
    return {"added": len(added), "scanned": len({f.get("page") for f in flags}),
            "issues": added}


@app.post("/api/feedback/{slug}/{entry_id}/disposition")
def set_disposition(slug: str, entry_id: str, body: DispositionBody):
    """Triage an issue: open | fixed | accepted | dismissed (+ optional note)."""
    if body.disposition not in ("open", "fixed", "accepted", "dismissed"):
        raise HTTPException(400, "bad disposition")
    path = _feedback_path(slug)
    if not path.exists():
        raise HTTPException(404, "no feedback for document")
    lines = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    for rec in lines:
        if rec.get("id") == entry_id:
            rec["disposition"] = body.disposition
            if body.note is not None:
                rec["dispositionNote"] = body.note
            rec["dispositionAt"] = datetime.datetime.now(
                datetime.timezone.utc).isoformat(timespec="seconds")
            path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                    for r in lines))
            return rec
    raise HTTPException(404, f"no entry {entry_id!r}")


@app.post("/api/feedback/{slug}/empty-trash")
def empty_trash(slug: str):
    path = _feedback_path(slug)
    if not path.exists():
        return {"emptied": 0}
    lines = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    kept = [r for r in lines if r.get("status") != "cleared"]
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept))
    return {"emptied": len(lines) - len(kept)}


@app.delete("/api/feedback/{slug}/{entry_id}")
def delete_feedback(slug: str, entry_id: str):
    path = _feedback_path(slug)
    if not path.exists():
        raise HTTPException(404, "no feedback for document")
    lines = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    kept = [r for r in lines if r.get("id") != entry_id]
    if len(kept) == len(lines):
        raise HTTPException(404, f"no feedback entry {entry_id!r}")
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept))
    return {"deleted": entry_id}


class EditOp(BaseModel):
    """Durable per-element edit: survives every re-render, applied at the
    render stage. One op per (nid, op) pair — posting again replaces.
    `reorder` is page-scoped (nid = "reorder-p<page>"): `order` lists the page's
    nids in the corrected reading order."""
    nid: str
    op: str  # set-text | delete | set-level | reorder | merge | note
    value: str | int | None = None
    page: int | None = None
    order: list[str] | None = None
    into: str | None = None  # merge target
    frm: str | None = None   # merge source (folded into `into`, then dropped)
    n: str | int | None = None  # note op: the footnote's index (4, "a", "iv")


def _ops_path(slug: str) -> Path:
    src = source_for_slug(slug)
    if src is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    return src.with_name(src.stem + ".ops.json")


def _read_ops(path: Path):
    return json.loads(path.read_text()) if path.exists() else []


@app.get("/api/ops/{slug}")
def get_ops(slug: str):
    return _read_ops(_ops_path(slug))


@app.post("/api/ops/{slug}")
def post_op(slug: str, op: EditOp):
    path = _ops_path(slug)
    ops = [o for o in _read_ops(path)
           if not (o["nid"] == op.nid and o["op"] == op.op)]
    ops.append(op.model_dump(exclude_none=True))
    path.write_text(json.dumps(ops, indent=1, ensure_ascii=False))
    _spawn_convert(slug)  # ops are in the render fingerprint: render-only
    return {"ops": len(ops), "status": "in_progress"}


@app.delete("/api/ops/{slug}/{op_kind}/{nid}")
def delete_op(slug: str, op_kind: str, nid: str):
    path = _ops_path(slug)
    ops = _read_ops(path)
    kept = [o for o in ops if not (o["nid"] == nid and o["op"] == op_kind)]
    if len(kept) == len(ops):
        raise HTTPException(404, "no such op")
    path.write_text(json.dumps(kept, indent=1, ensure_ascii=False))
    _spawn_convert(slug)
    return {"ops": len(kept), "status": "in_progress"}


# ---- pattern-identification worktrack (read-only consumer + review writer) --
# The pattern agent owns patterns/ and emits regenerable per-doc reports to
# patterns/out/ (see sources/docs/plans/rk3-pattern-identification-worktrack-
# plan.md §23). The app READS those reports and WRITES review decisions in the
# agent's own format (patterns/schemas/review-decision.schema.json) to
# patterns/review-decisions/<slug>.jsonl — the agreed seam, nothing else.

PATTERNS_OUT = ROOT / "patterns" / "out"
PATTERNS_DECISIONS = ROOT / "patterns" / "review-decisions"


class PatternDecision(BaseModel):
    pattern_id: str
    decision: str  # accept | reject | accept_with_edits | wrong_type | …
    pattern_type: Optional[str] = None
    notes: Optional[str] = None


def _pattern_decisions(slug: str) -> dict:
    f = PATTERNS_DECISIONS / f"{slug}.jsonl"
    out = {}
    if f.exists():
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            try:
                e = json.loads(line)
                out[e["pattern_id"]] = e  # last decision wins
            except (json.JSONDecodeError, KeyError):
                continue
    return out


@app.get("/api/patterns")
def patterns_index():
    """Aggregate view: one row per analyzed doc — inventory, totals, review
    progress, and the input stamp for staleness checks."""
    rows = []
    for p in sorted(PATTERNS_OUT.glob("*.json")) if PATTERNS_OUT.is_dir() else []:
        try:
            r = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        slug = r.get("document_id") or p.stem
        cands = r.get("candidates") or []
        rows.append({
            "slug": slug,
            "schema": r.get("schema"),
            "input": r.get("input"),
            "inventory": r.get("pattern_inventory") or {},
            "total": len(cands),
            "decided": len(_pattern_decisions(slug)),
            "warnings": len(r.get("warnings") or []),
        })
    return rows


@app.get("/api/patterns/{slug}")
def patterns_doc(slug: str):
    f = PATTERNS_OUT / f"{slug}.json"
    if not f.exists():
        raise HTTPException(404, f"no pattern report for {slug!r}")
    r = json.loads(f.read_text())
    r["decisions"] = _pattern_decisions(slug)
    return r


@app.post("/api/patterns/{slug}/decision")
def pattern_decide(slug: str, d: PatternDecision):
    PATTERNS_DECISIONS.mkdir(parents=True, exist_ok=True)
    rec = {"schema": 1, "document_id": slug, "pattern_id": d.pattern_id,
           "decision": d.decision, "reviewer": "owner",
           "reviewed_at": datetime.datetime.now(datetime.timezone.utc)
                          .isoformat()}
    if d.pattern_type:
        rec["pattern_type"] = d.pattern_type
    if d.notes:
        rec["notes"] = d.notes
    with open(PATTERNS_DECISIONS / f"{slug}.jsonl", "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {"ok": True, "decided": len(_pattern_decisions(slug))}


# ---------------------------------------------------------------- landing page
# The Landing Page Maker builds an SEO/AEO/a11y landing page from a document.
# Config + theme are the editable source of truth; they're stored next to the
# source PDF (like edit ops) so they survive output regeneration. Defaults are
# derived from ir.json on first access and only persisted once the user edits.

def _ir_for(slug: str) -> dict:
    ir_path = output_dir(slug) / "ir.json"
    if not ir_path.exists():
        raise HTTPException(404, f"{slug!r} has no IR yet (not converted)")
    return json.loads(ir_path.read_text())


def _landing_path(slug: str, suffix: str) -> Path:
    src = source_for_slug(slug)
    if src is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    return src.with_name(src.stem + suffix)


def _doc_name(slug: str) -> str:
    src = source_for_slug(slug)
    return src.name if src else ""


def _landing_ai(slug: str, ir: dict) -> dict | None:
    """The cached AI pass (next to the source, so it runs once per doc and
    survives output regeneration). Runs by tier: analyze locates the intro
    section (a pointer), generate also authors title/summaries/findings. Returns
    None when AI is off or nothing succeeded — callers fall back to heuristics."""
    path = _landing_path(slug, ".landing-ai.json")
    if path.exists():
        return json.loads(path.read_text())
    data: dict = {}
    if ai_can_analyze():
        try:
            heading = find_intro_section(ir)
            if heading:
                data["intro_heading"] = heading
        except Exception:
            pass
        try:  # verbatim at analyze, lightly-edited at generate
            data["findings"] = find_findings(ir, verbatim=not ai_can_generate())
        except Exception:
            pass
    if ai_can_generate():
        try:
            data.update(generate_landing_ai(ir))
        except Exception:  # any provider/parse error -> heuristics
            pass
    if not data:
        return None
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return data


@app.get("/api/landing/{slug}")
def get_landing(slug: str):
    path = _landing_path(slug, ".landing.json")
    if path.exists():
        return json.loads(path.read_text())
    ir = _ir_for(slug)
    return build_config(ir, name=_doc_name(slug), ai=_landing_ai(slug, ir))


@app.get("/api/landing/{slug}/template/{archetype}")
def get_landing_template(slug: str, archetype: str):
    """Re-seed the page from a chosen archetype (the template switcher).
    Returns a fresh config but does not persist — the client saves on edit."""
    ir = _ir_for(slug)
    return build_config(ir, name=_doc_name(slug), archetype=archetype, ai=_landing_ai(slug, ir))


@app.get("/api/landing/{slug}/block-defaults")
def get_block_defaults(slug: str):
    """Document-aware default props per block type (for prepopulate-on-insert)."""
    ir = _ir_for(slug)
    return block_defaults(ir, name=_doc_name(slug), ai=_landing_ai(slug, ir))


@app.post("/api/landing/{slug}/ai-refresh")
def refresh_landing_ai(slug: str):
    """Discard the cached AI content and regenerate it (no admin UI yet)."""
    _landing_path(slug, ".landing-ai.json").unlink(missing_ok=True)
    ai = _landing_ai(slug, _ir_for(slug))
    return {"refreshed": ai is not None}


@app.get("/api/landing/{slug}/ai-summary")
def get_ai_summary(slug: str, style: str, length: str):
    """Lazily generate (and cache) one AI summary variant for a (style, length).
    Returns {"text": ...}; empty string when AI is off or generation fails."""
    ir = _ir_for(slug)
    _landing_ai(slug, ir)  # ensure the base cache (title/highlights/default summaries) exists
    path = _landing_path(slug, ".landing-ai.json")
    data = json.loads(path.read_text()) if path.exists() else {}
    key = f"{style}:{length}"
    cached = (data.get("summaries") or {}).get(key)
    if cached is not None:
        return {"text": cached}
    if not ai_can_generate():
        return {"text": ""}
    try:
        text = generate_summary_variant(ir, style, length)
    except Exception:
        return {"text": ""}
    data.setdefault("summaries", {})[key] = text
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return {"text": text}


@app.get("/api/landing-archetypes")
def landing_archetypes():
    return ARCHETYPE_LABELS


@app.get("/api/ai-mode")
def get_ai_mode():
    """The AI tier (none | analyze | generate), so the editor can gate features."""
    return {"mode": ai_mode()}


@app.post("/api/landing/{slug}")
def post_landing(slug: str, config: dict):
    path = _landing_path(slug, ".landing.json")
    path.write_text(json.dumps(config, indent=1, ensure_ascii=False))
    return {"saved": True, "blocks": len(config.get("blocks", []))}


@app.get("/api/landing-theme/{slug}")
def get_landing_theme(slug: str):
    path = _landing_path(slug, ".landing-theme.json")
    if path.exists():
        return json.loads(path.read_text())
    return build_default_theme(_ir_for(slug))


@app.post("/api/landing-theme/{slug}")
def post_landing_theme(slug: str, theme: dict):
    path = _landing_path(slug, ".landing-theme.json")
    path.write_text(json.dumps(theme, indent=1, ensure_ascii=False))
    return {"saved": True}


@app.get("/api/source/{slug}")
def get_source(slug: str):
    """The original PDF — powers the landing page Download CTA and lets the
    export bundle the file into the zip."""
    src = source_for_slug(slug)
    if src is None or not src.exists():
        raise HTTPException(404, f"unknown document {slug!r}")
    return FileResponse(src, media_type="application/pdf", filename=src.name)


OUTPUT.mkdir(parents=True, exist_ok=True)
app.mount("/output", StaticFiles(directory=OUTPUT), name="output")

_dist = Path(__file__).parent / "ui" / "dist"
_static = _dist if _dist.is_dir() else Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=_static, html=True), name="viewer")
