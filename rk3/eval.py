"""Conversion eval harness — data-driven spot-tests over the per-stage artifacts.

Each document has a spec at eval/<slug>.yaml listing checks. A check asserts an
OUTCOME against the converted artifacts:

  - order: [A, B]              A's text must read before B's  (catches column shuffles)
  - role:  {text, is, level?}  a node's type / heading level  (catches missed/spurious headings)
  - list:  [I1, I2, ...]       these snippets are items of ONE list, in order
                               (catches un-reconstructed bullets and split lists)
  - merge: [A, B]              A and B belong to ONE node (catches over-split paragraphs)
  - freeze: {anchor, html}     the element's SEMANTIC content (text + em/strong/a +
                               list/heading structure) must stay exactly as captured.
                               The general "this bit is correct, don't let it change"
                               primitive — derived from the IR, so data-*/CSS are ignored.

Checks anchor to content by text snippet — the same thing a future "create
assertion" right-click in the review UI would capture from a selection. On a
failure we localize to the earliest stage where the anchor breaks, so a
mis-ordering in the final IR isn't mistaken for an upstream extraction loss.

Runs through convert() so the per-stage fingerprint cache applies: the PDF is
opened once and only stages whose code VERSION / config / source changed re-run.

    python -m rk3 eval [slug]
"""

import json
import re

import yaml

from . import irwalk
from .documents import ROOT, output_dir
from .pipeline import ARTIFACTS, convert

EVAL_DIR = ROOT / "eval"


def _norm(s):
    if isinstance(s, dict):  # list items may carry emphasis/link runs
        s = s.get("text", "")
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _walk(body):
    yield from irwalk.walk(body)


def _artifact(slug, stage):
    p = output_dir(slug) / ARTIFACTS[stage]
    return json.loads(p.read_text()) if p.exists() else None


STAGES = ("extract", "assemble", "analyze", "render")


def _stage_seq(slug, stage):
    """A stage's content as an ordered list of {text, type, level} — so a check
    can assert against the layer where the property actually lives.

      analyze  → IR text nodes (paragraphs/headings) with type + level
      assemble → blocks in stored order (text = joined lines; no type/level yet)
      extract  → one entry per page (concatenated chars)
    """
    if stage == "analyze":
        ir = _artifact(slug, "analyze") or {}
        return [{"text": n.get("text", ""), "type": n.get("type"), "level": n.get("level")}
                for n in _walk(ir.get("body", []))
                if n.get("type") in ("paragraph", "heading") and n.get("text")]
    if stage == "assemble":
        b = _artifact(slug, "assemble") or {}
        return [{"text": " ".join(ln.get("text", "") for ln in blk.get("lines", [])),
                 "type": None, "level": None, "page": blk.get("page")}
                for blk in b.get("blocks", [])]
    if stage == "extract":
        e = _artifact(slug, "extract") or {}
        return [{"text": "".join(c[0] for c in p.get("chars", [])),
                 "type": None, "level": None, "page": p.get("n")}
                for p in e.get("pages", [])]
    return []


def _find(seq, snippet):
    s = _norm(snippet)
    for i, n in enumerate(seq):
        if s in _norm(n.get("text")):
            return i
    return -1


def _blocks_has(slug, snippet):
    b = _artifact(slug, "assemble")
    if not b:
        return False
    text = _norm(" ".join(ln.get("text", "")
                          for blk in b.get("blocks", []) for ln in blk.get("lines", [])))
    return _norm(snippet) in text


def _localize(slug, snippet):
    """Point at the defect's stage: present by `assemble` → it's an analyze bug;
    gone by then → the text was lost in extract/assemble."""
    if _blocks_has(slug, snippet):
        return "present in assemble → defect is in analyze (ordering/typing)"
    return "missing by assemble → defect is upstream (extract/assemble lost the text)"


# ---- check evaluators: (ok, detail). Each reads the check's target stage. ----
def _check_order(slug, c):
    stage = c.get("stage", "analyze")
    seq = _stage_seq(slug, stage)
    a, b = c["order"]
    ia, ib = _find(seq, a), _find(seq, b)
    if ia < 0:
        return False, f"{a!r} not found in {stage} — {_localize(slug, a)}"
    if ib < 0:
        return False, f"{b!r} not found in {stage} — {_localize(slug, b)}"
    if ia == ib:
        # both snippets in ONE node: a column-wrap join legitimately fuses a
        # sentence that flows across the gutter — the reading-order intent is
        # satisfied iff A's text precedes B's WITHIN the node
        t = _norm(seq[ia].get("text"))
        oa, ob = t.find(_norm(a)), t.find(_norm(b))
        if oa < ob:
            return True, f"both in node #{ia}, {a!r} first (joined flow)"
        return False, f"both in node #{ia} but {a!r} reads AFTER {b!r} inside it"
    if ia < ib:
        return True, f"{a!r} (#{ia}) before {b!r} (#{ib})"
    return False, f"{a!r} (#{ia}) reads AFTER {b!r} (#{ib}) — {_localize(slug, a)}"


def _check_role(slug, c):
    stage = c.get("stage", "analyze")
    if stage != "analyze":
        return False, f"role checks need the analyze stage (got {stage!r})"
    seq = _stage_seq(slug, "analyze")
    r = c["role"]
    i = _find(seq, r["text"])
    if i < 0:
        return False, f"{r['text']!r} not found in analyze — {_localize(slug, r['text'])}"
    n = seq[i]
    is_h = n.get("type") == "heading"
    want = r.get("is", "heading")
    if want == "not-heading":
        return (not is_h), (f"is a {n.get('type')}" if not is_h
                            else "is a heading, expected non-heading")
    if not is_h:
        return False, f"is a {n.get('type')}, expected heading"
    if "level" in r and n.get("level") != r["level"]:
        return False, f"heading level {n.get('level')}, expected {r['level']}"
    return True, "heading" + (f" level {n.get('level')}" if "level" in r else "")


def _list_nodes(slug):
    ir = _artifact(slug, "analyze") or {}
    return [n for n in _walk(ir.get("body", [])) if n.get("type") == "list"]


def _list_items(node):
    """A list's items as text-dicts, for both IR shapes: legacy `items`
    (runs-dicts) and the unified container shape (item nodes whose first
    text leaf carries the item's text/runs)."""
    if node.get("items") is not None:
        return node["items"]
    out = []
    for it in node.get("children") or []:
        leaf = next((ch for ch in (it.get("children") or [])
                     if ch.get("text")), None)
        out.append(leaf if leaf is not None else {"text": ""})
    return out


def _check_list(slug, c):
    """All snippets must be items of a SINGLE list node, in order — pins missing
    list reconstruction (snippet lives in no list) and over-split lists (snippets
    scatter across separate lists, e.g. a UL broken over a page break). Optional
    `ordered:` asserts the host list's type (decimal/lower-alpha/…) — pins a
    numbered list that should be an <ol> with the markers stripped."""
    snippets = c["list"]
    lists = _list_nodes(slug)
    s0 = _norm(snippets[0])
    host = next((ln for ln in lists
                 if any(s0 in _norm(it) for it in _list_items(ln))), None)
    if host is None:
        return False, f"first item {snippets[0]!r} is in no list — {_localize(slug, snippets[0])}"
    want_ord = c.get("ordered")
    if want_ord is not None and host.get("ordered") != want_ord:
        return False, (f"list is ordered={host.get('ordered')!r}, expected {want_ord!r}"
                       " — numbered list not emitted as <ol> (markers still in text?)")
    items = [_norm(it) for it in _list_items(host)]
    last = -1
    for sn in snippets:
        ns = _norm(sn)
        pos = next((i for i in range(last + 1, len(items)) if ns in items[i]), -1)
        if pos < 0:
            split = any(ns in _norm(it) for o in lists
                        if o is not host for it in _list_items(o))
            why = ("is in a different list (list split)" if split
                   else f"is not a list item — {_localize(slug, sn)}")
            return False, f"item {sn!r} {why}"
        last = pos
    return True, f"{len(snippets)} items in one list (#{lists.index(host)})"


def _check_merge(slug, c):
    """A and B should live in ONE text node — pins over-split paragraphs."""
    a, b = c["merge"]
    seq = _stage_seq(slug, "analyze")
    ia, ib = _find(seq, a), _find(seq, b)
    if ia < 0:
        return False, f"{a!r} not found — {_localize(slug, a)}"
    if ib < 0:
        return False, f"{b!r} not found — {_localize(slug, b)}"
    if ia == ib:
        return True, f"both in node #{ia}"
    return False, f"{a!r} (#{ia}) and {b!r} (#{ib}) are separate — should be one paragraph"


def _check_split(slug, c):
    """A and B must live in SEPARATE text nodes — the inverse of merge. Pins
    column fusion: two columns' text welded into one paragraph (the
    advancing-mobility p12 class, where a new column's opening sentence lands
    mid-node)."""
    a, b = c["split"]
    seq = _stage_seq(slug, "analyze")
    ia, ib = _find(seq, a), _find(seq, b)
    if ia < 0:
        return False, f"{a!r} not found — {_localize(slug, a)}"
    if ib < 0:
        return False, f"{b!r} not found — {_localize(slug, b)}"
    if ia != ib:
        return True, f"separate nodes (#{ia}, #{ib})"
    return False, (f"{a!r} and {b!r} are FUSED in node #{ia} — "
                   "should be separate (column/paragraph fusion)")


# ---- freeze: the general "this bit is correct, keep it" primitive ----
# A reviewer selects a rendered element and freezes its SEMANTIC content — the
# text plus the <em>/<strong>/<a> and list/heading structure, woven from the IR.
# Derived from the IR (not the HTML string), so data-*, generated class names and
# CSS are ignored by construction; it breaks iff the content/marks actually change.

def _merge_links(links):
    out = []
    for s, e, tgt in sorted(links or []):
        uri = (tgt or {}).get("uri") if isinstance(tgt, dict) else tgt
        if out and s - out[-1][1] <= 1 and out[-1][2] == uri:
            out[-1][1] = e
        else:
            out.append([s, e, uri])
    return out


def _weave(text, emph, links):
    """Text with <a>/<strong>/<em> woven in at their IR offsets (link outer,
    emphasis inner) — a stable, readable, CSS-free rendering of the marks.

    Spans that cross are split at the boundary and reopened so the output is
    always well-formed (link[10,20]+em[15,25] -> <a>…<em>…</em></a><em>…</em>),
    mirroring render._inline so freeze snapshots match what we actually emit."""
    rank = {"link": 0, "strong": 1, "em": 2}
    wraps = []  # (s, e, rank, open, close)
    for s, e, uri in _merge_links(links):
        wraps.append((s, e, rank["link"], f'<a href="{uri or ""}">', "</a>"))
    for sp in emph or []:
        s, e, kind = sp[0], sp[1], sp[2]
        if kind in rank:
            wraps.append((s, e, rank[kind], f"<{kind}>", f"</{kind}>"))
    n = len(text)
    pts = sorted({0, n} | {p for s, e, *_ in wraps for p in (s, e)
                           if 0 <= p <= n})
    out, stack = [], []
    for a, b in zip(pts, pts[1:]):
        if a >= b:
            continue
        active = sorted((w for w in wraps if w[0] <= a and b <= w[1]),
                        key=lambda w: (w[2], w[0], -w[1]))
        cp = 0
        while cp < len(stack) and cp < len(active) and stack[cp] is active[cp]:
            cp += 1
        while len(stack) > cp:
            out.append(stack.pop()[4])
        for w in active[cp:]:
            out.append(w[3])
            stack.append(w)
        out.append(text[a:b])
    while stack:
        out.append(stack.pop()[4])
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _canonical(node):
    """The frozen semantic form of a node."""
    t = node.get("type")
    if t == "heading":
        lvl = node.get("level", "")
        return f"<h{lvl}>{_weave(node.get('text', ''), node.get('emph'), node.get('links'))}</h{lvl}>"
    if t == "paragraph":
        return _weave(node.get("text", ""), node.get("emph"), node.get("links"))
    if t == "list":
        tag = "ol" if node.get("ordered") else "ul"
        otype = f' type="{node["ordered"]}"' if node.get("ordered") else ""
        lis = []
        for it in _list_items(node):
            if isinstance(it, dict):
                lis.append(f"<li>{_weave(it.get('text', ''), it.get('emph'), it.get('links'))}</li>")
            else:
                lis.append(f"<li>{re.sub(r'\\s+', ' ', it).strip()}</li>")
        return f"<{tag}{otype}>" + "".join(lis) + f"</{tag}>"
    return _norm(node.get("text", ""))


def _anchor_of(node):
    """A text snippet that relocates a node across reconverts (nids change)."""
    if node.get("text"):
        return node["text"][:60]
    for it in _list_items(node) if node.get("type") == "list" else []:
        txt = it.get("text") if isinstance(it, dict) else it
        if txt:
            return txt[:60]
    return ""


def canonical_for_nid(slug, nid):
    """(anchor, canonical) for the node with this nid — backs the UI's freeze
    capture/preview. Returns None if not found."""
    ir = _artifact(slug, "analyze") or {}
    for n in _walk(ir.get("body", [])):
        if n.get("nid") == nid:
            return _anchor_of(n), _canonical(n)
    return None


def _check_freeze(slug, c):
    """The element located by `anchor` still renders the exact frozen content.
    An anchor may legitimately match several nodes (the unified container model
    made table-cell text real, so a heading's phrase can also appear in a
    summary cell): the freeze holds if ANY matching node still renders the
    frozen HTML exactly; only if none does is it a change."""
    spec = c["freeze"]
    anchor, want = spec.get("anchor", ""), spec.get("html", "")
    ir = _artifact(slug, "analyze") or {}
    first = None
    for n in _walk(ir.get("body", [])):
        if n.get("type") not in ("paragraph", "heading", "list"):
            continue
        if _norm(anchor) and _norm(anchor) in _norm(_canonical(n)):
            got = _canonical(n)
            if got == want:
                return True, "content unchanged"
            if first is None:
                first = got
    if first is not None:
        return False, f"changed:\n      was: {want}\n      now: {first}"
    return False, f"element {anchor[:40]!r} not found — {_localize(slug, anchor)}"


EVALUATORS = {"order": _check_order, "role": _check_role, "list": _check_list,
              "merge": _check_merge, "split": _check_split,
              "freeze": _check_freeze}


def evaluate_check(slug, check):
    """Run ONE check against the doc's current artifacts (no reconvert) and
    return (ok, detail) — the engine behind the review UI's 'create assertion'
    QA step. Raises ValueError on an unknown/empty check."""
    if _artifact(slug, "analyze") is None:
        return False, "no ir.json — convert the document first"
    kind = next((k for k in EVALUATORS if k in check), None)
    if not kind:
        raise ValueError(f"check has no known kind (one of {sorted(EVALUATORS)})")
    return EVALUATORS[kind](slug, check)


def _check_anchor(check, kind):
    """The text snippet that locates a check's primary element."""
    if kind == "freeze":
        return check["freeze"].get("anchor")
    if kind == "role":
        return check["role"].get("text")
    if kind in ("merge", "order"):
        return (check[kind] or [None])[0]
    if kind == "list":
        return (check["list"] or [None])[0]
    return None


def checks_with_status(slug):
    """Every check on the doc, evaluated against the CURRENT artifacts, with
    the nid of its anchoring element — backs the viewer's assertion markers
    (⚑ green = passing stake, red = failing / regression target)."""
    path = EVAL_DIR / f"{slug}.yaml"
    if not path.exists():
        return []
    spec = yaml.safe_load(path.read_text()) or {}
    ir = _artifact(slug, "analyze") or {}
    nodes = [n for n in _walk(ir.get("body", []))
             if n.get("type") in ("paragraph", "heading", "list")]
    out = []
    for i, c in enumerate(spec.get("checks", [])):
        kind = next((k for k in EVALUATORS if k in c), None)
        if kind:
            try:
                ok, detail = EVALUATORS[kind](slug, c)
            except Exception as e:  # a malformed check must not hide the rest
                ok, detail = False, f"check error: {e}"
        else:
            ok, detail = False, "unknown check kind"
        anchor, nid = _check_anchor(c, kind), None
        if anchor and _norm(anchor):
            na = _norm(anchor)
            # match canonical (markup-aware) OR plain text — an anchor spanning
            # an emphasis boundary has tags inside its canonical form
            def _plain(n):
                its = _list_items(n) if n.get("type") == "list" else []
                return " ".join([n.get("text") or "",
                                 *(_norm(i) for i in its)])
            nid = next((n.get("nid") for n in nodes
                        if na in _norm(_canonical(n)) or na in _norm(_plain(n))),
                       None)
        out.append({"i": i, "kind": kind, "note": c.get("note"),
                    "stage": c.get("stage", "analyze"),
                    "ok": ok, "detail": detail, "nid": nid})
    return out


def append_check(slug, check):
    """Append a validated check to eval/<slug>.yaml (creating the spec if new).
    A TEXTUAL append — the existing file (incl. its rationale comments) is left
    byte-for-byte intact; only the new check block is added under `checks:`.
    Returns the total number of checks now on the doc."""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    path = EVAL_DIR / f"{slug}.yaml"
    dumped = yaml.safe_dump([check], sort_keys=False, allow_unicode=True, width=100)
    block = "".join(("  " + ln) if ln.strip() else ln
                    for ln in dumped.splitlines(keepends=True))  # nest under checks:
    if not path.exists():
        path.write_text(f"doc: {slug}\nchecks:\n{block}")
        return 1
    text = path.read_text()
    if "\nchecks:" not in text and not text.startswith("checks:"):
        text = text.rstrip() + "\nchecks:\n"
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n" + block)
    spec = yaml.safe_load(path.read_text()) or {}
    return len(spec.get("checks", []))


def _eval_doc(path):
    spec = yaml.safe_load(path.read_text())
    slug = spec["doc"]
    convert(slug)  # cached; re-runs only changed stages
    print(f"\n{slug}")
    if _artifact(slug, "analyze") is None:
        print("  ! no ir.json (conversion failed?)")
        return 0, len(spec.get("checks", []))
    npass = nfail = 0
    for c in spec.get("checks", []):
        kind = next((k for k in EVALUATORS if k in c), None)
        stage = c.get("stage", "analyze")
        if not kind:
            print(f"  ????  {c.get('note', '(no note)')}: unknown check kind")
            nfail += 1
            continue
        ok, detail = EVALUATORS[kind](slug, c)
        print(f"  {'PASS' if ok else 'FAIL'}  [{stage:>8}]  {c.get('note', '')}")
        if not ok:
            print(f"             ↳ {detail}")
        npass += ok
        nfail += not ok
    return npass, nfail


def run(slug=None):
    files = [EVAL_DIR / f"{slug}.yaml"] if slug else sorted(EVAL_DIR.glob("*.yaml"))
    files = [f for f in files if f.exists()]
    if not files:
        print(f"no eval specs found in {EVAL_DIR}")
        return 2
    P = F = 0
    for f in files:
        p, q = _eval_doc(f)
        P, F = P + p, F + q
    print(f"\n{'=' * 50}\n{P} passed, {F} failed")
    return 1 if F else 0
