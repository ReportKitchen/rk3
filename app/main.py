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

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rk3.documents import OUTPUT, list_documents, output_dir, source_for_slug
from rk3.landing.extract import build_default_config, build_default_theme

ROOT = Path(__file__).resolve().parent.parent
FEEDBACK = ROOT / "feedback"

app = FastAPI(title="RK3")

_active: set[str] = set()
_active_lock = threading.Lock()


@app.get("/api/documents")
def documents():
    docs = list_documents()
    with _active_lock:
        for d in docs:
            if d["slug"] in _active:
                d["status"] = "in_progress"
    return docs


@app.post("/api/convert/{slug}")
def start_convert(slug: str, force: bool = False):
    if source_for_slug(slug) is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    _spawn_convert(slug, force)
    return {"slug": slug, "status": "in_progress"}


def _spawn_convert(slug: str, force: bool = False):
    with _active_lock:
        if slug in _active:
            return
        _active.add(slug)

    def work():
        try:
            cmd = [sys.executable, "-m", "rk3", "convert", slug]
            if force:
                cmd.append("--force")
            subprocess.run(cmd, cwd=ROOT, timeout=3600,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        finally:
            with _active_lock:
                _active.discard(slug)

    threading.Thread(target=work, daemon=True, name=f"convert-{slug}").start()


class FeedbackEntry(BaseModel):
    """One viewer annotation. Either an element target (nid/rk) or a PDF-pane
    spot (page + fractional coords). type: "comment" | "answer".
    Answers carry qid + choice. This same stream later feeds the in-codebase
    config agent; during development Claude reads it directly."""
    type: str = "comment"
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
    render stage. One op per (nid, op) pair — posting again replaces."""
    nid: str
    op: str  # set-text | delete | set-level
    value: str | int | None = None


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


@app.get("/api/landing/{slug}")
def get_landing(slug: str):
    path = _landing_path(slug, ".landing.json")
    if path.exists():
        return json.loads(path.read_text())
    return build_default_config(_ir_for(slug))


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
