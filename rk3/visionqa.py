"""Vision-QA reviewer (analysis-only).

Screenshots our rendered output, cropped per ORIGINAL page via the `data-page`
provenance, and asks a vision model to flag discrepancies against the original
page image. It is a REVIEWER — it flags, it never edits. The conversion rubric
is injected so the model tells an intentional transform (single column, no page
breaks, dropped underlines …) from a real error.
"""

import json
from pathlib import Path

from rk3 import irwalk
from rk3.ai import vision_json
from rk3.documents import output_dir

ROOT = Path(__file__).resolve().parent.parent
RUBRIC = ROOT / "sources" / "docs" / "conversion-rubric.md"
BASE = "http://127.0.0.1:8300"

_BBOX_JS = """(p) => {
  const els = [...document.querySelectorAll(`[data-page="${p}"]`)];
  if (!els.length) return null;
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  for (const e of els) { const r = e.getBoundingClientRect();
    x0=Math.min(x0,r.left+scrollX); y0=Math.min(y0,r.top+scrollY);
    x1=Math.max(x1,r.right+scrollX); y1=Math.max(y1,r.bottom+scrollY); }
  return {x:Math.max(0,x0-8), y:Math.max(0,y0-8),
          width:(x1-x0)+16, height:(y1-y0)+16};
}"""


def shoot(slug, pages=None, width=900):
    """Screenshot our rendered output cropped to each original page's content.
    Returns {page: png_path}."""
    from playwright.sync_api import sync_playwright

    url = f"{BASE}/output/pdfium/{slug}/index.html"
    qadir = output_dir(slug) / "qa"
    qadir.mkdir(exist_ok=True)
    out = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": width, "height": 1400},
                              device_scale_factor=2)
        pg.goto(url, wait_until="networkidle")
        if pages is None:
            pages = pg.evaluate(
                "[...new Set([...document.querySelectorAll('[data-page]')]"
                ".map(e=>+e.getAttribute('data-page')))].sort((a,b)=>a-b)")
        for p in pages:
            box = pg.evaluate(_BBOX_JS, p)
            if not box:
                continue
            path = qadir / f"our-page-{p:04d}.png"
            pg.screenshot(path=str(path), clip=box, full_page=True)
            out[p] = path
        browser.close()
    return out


_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "flags": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "category": {"type": "string", "enum": [
                        "structure", "emphasis-style", "spacing", "missing-content",
                        "extra-content", "reading-order", "table", "figure",
                        "link", "color", "other"]},
                    "kind": {"type": "string", "enum": ["error", "opportunity"]},
                    "severity": {"type": "string", "enum": [
                        "critical", "high", "medium", "low"]},
                    "where": {"type": "string"},
                    "issue": {"type": "string"},
                    "fix": {"type": "string"},
                },
                "required": ["category", "kind", "severity", "where", "issue", "fix"],
            },
        }
    },
    "required": ["flags"],
}

_BASE_SYSTEM = (
    "You are a meticulous QA reviewer for a PDF-to-HTML conversion engine. You are "
    "given two images: IMAGE 1 is the ORIGINAL PDF page; IMAGE 2 is OUR web-optimized "
    "conversion of that page's content. Compare them and flag DISCREPANCIES where our "
    "output fails to faithfully represent the original.\n\n"
    "Use the conversion rubric below to distinguish an INTENTIONAL TRANSFORM (e.g. single "
    "column, no page breaks, dropped link underlines, TOC removed) — which you must NOT "
    "flag — from a fixable problem.\n\n"
    "Classify each flag's KIND:\n"
    "- 'error' — a fidelity FAILURE: lost content, wrong reading order, dropped emphasis, "
    "broken link, mis-spaced words ('b y'), content in the wrong container, a heading "
    "missed or mis-leveled, a figure/table dropped.\n"
    "- 'opportunity' — the conversion is faithful but a web-optimization the rubric allows "
    "would help (e.g. links not visually distinct enough; a data table kept as an image "
    "that could be real HTML; contrast a touch low).\n\n"
    "TWO FAILURE MODES ARE EASY TO MISS — hunt for them explicitly on every page:\n"
    "1. DUPLICATED CONTENT (critical error). The SAME content appearing TWICE in IMAGE 2 — "
    "a title, heading, banner, logo, or block. This is EASY TO MISS when the two copies look "
    "different: one copy may be a RASTER IMAGE (a cropped banner/header/logo bitmap) while the "
    "other is LIVE TEXT of the same words; or one is a big heading and the other sits inside a "
    "box or figure. If you can read the same phrase in two places, it is duplicated — flag it "
    "critical. Do NOT excuse it as a figure plus a heading; the reader is seeing one thing "
    "twice. The ONLY allowed repeat is a genuine pull-quote that re-quotes a sentence of body "
    "text on purpose — a whole banner/title/header repeated is never that.\n"
    "2. WRONG BACKGROUND / FILL (high error, not low). A container whose fill color is wrong "
    "in a way that changes its whole appearance: a box the original shows WHITE or light "
    "rendered dark or colored; a header-strip color smeared across an ENTIRE box; a callout "
    "that lost or swapped its fill. Rate this HIGH — 'same look, same colors' is the bar. Do "
    "NOT downgrade it to low because the text is still legible, and do NOT report only a minor "
    "detail (alignment, centering) while missing that the whole box is the wrong color.\n\n"
    "SEVERITY: critical (content/meaning lost, incl. duplicated content) / high (a whole "
    "element looks wrong — wrong fill, wrong container, missing figure) / medium / low. Give a "
    "one-line 'fix'. If the conversion is faithful with no opportunities, return an empty list. "
    "Be specific and locatable. You are a REVIEWER, not an editor — describe, never rewrite."
)


def _system():
    rubric = RUBRIC.read_text() if RUBRIC.exists() else "(rubric not found)"
    return f"{_BASE_SYSTEM}\n\n=== CONVERSION RUBRIC ===\n{rubric}"


def qa_page(slug, page, our_png=None, model=None):
    """Flag discrepancies for one page (image-vs-image). Returns the flags list.
    model: override the reviewer model (e.g. claude-haiku-4-5 for cheap sweeps)."""
    orig = output_dir(slug) / "pages" / f"page-{page:04d}.png"
    if our_png is None:
        our_png = output_dir(slug) / "qa" / f"our-page-{page:04d}.png"
    user = ("IMAGE 1 is the ORIGINAL page. IMAGE 2 is OUR conversion of that page's "
            "content (reflowed to a single web column). Flag only real discrepancies, "
            "per the rubric — intentional transforms are not errors.")
    res = vision_json(_system(), user, [orig, our_png], _SCHEMA, max_tokens=4000, model=model)
    return res.get("flags", [])


def qa_doc(slug, pages=None, model=None):
    """Run vision-QA across a doc's pages (screenshots in one browser session).
    Returns a flat list of flags, each tagged with its source page."""
    shots = shoot(slug, pages=pages)
    out = []
    for page in sorted(shots):
        for f in qa_page(slug, page, our_png=shots[page], model=model):
            f["page"] = page
            out.append(f)
    return out


# ---------------------------------------------------------------------------
# The prescriber (webified §4.1): vision stops complaining and starts
# PRESCRIBING. Given the original page, our render, the page's IR skeleton and
# the lever catalog, it returns the MINIMAL set of per-document overrides that
# would make our structure match the original — anything no lever expresses
# goes to `residuals` with a named missingLever.
# ---------------------------------------------------------------------------

# lever names the prescriber may target; apply-time (§4.2) re-validates each
LEVER_NAMES = ["regionOverrides", "figureBands", "orderPins", "floatPins",
               "headingOverrides", "breakOverrides", "indentOverrides",
               "tablePins"]

_LEVER_CATALOG = """AVAILABLE OVERRIDE LEVERS (each is a per-document config entry; write the
MINIMAL set; anything you cannot express goes to `residuals`):

- regionOverrides {"page":n,"bbox":[l,b,r,t],"kind":"figure"|"callout"|"text"}
    reclassify a detected region. kind="text" DISSOLVES decoration (a watermark
    / faint shape mis-read as a box) back into ordinary flow.
- figureBands {"page":n,"bbox":[l,b,r,t],"title":"text-prefix"|null,"floor":y|null}
    force a chart/figure to assemble as ONE figure over the bbox (for charts the
    kicker heuristic misses — bubble charts, unkickered charts).
- orderPins {"page":n,"sequence":["text-prefix",...]}
    fix a page's reading order; list the blocks in the order they should read.
- floatPins {"nid":"..." | "textPrefix":"...","float":"left"|"right"|"none"|"wide"}
    set the float side of a FIGURE or a pull-quote PARAGRAPH/ASIDE (a side-quote
    that should sit in a column with body text beside it → float:left/right); none
    = full-width in flow.
- headingOverrides {"textPrefix":"...","level":1..6}  (level 0 = NOT a heading)
    Use level 0 for a mis-tagged heading that is really body/label text — e.g. a
    short ALL-CAPS ATTRIBUTION line directly under a pull-quote ("NONPROFIT LEADER",
    "— JANE DOE") is the quote's speaker, NOT a section heading.
- breakOverrides {"textPrefix":"...","breaks":true|false}   keep/join hard line breaks
- indentOverrides {"textPrefix":"...","mode":"preserve"|"remove"}
- tablePins {"page":n,"bbox":[l,b,r,t],"cols":[x-cut,...]|null,"headerRows":0|1}
    force a bbox to render as a real table.

bbox coordinates are PDF points (origin bottom-left), matching the IR skeleton
below. Prefer a text-prefix match over a bbox when the target has text."""

_PRESCRIBE_SYSTEM = (
    "You are the PRESCRIBER for a PDF-to-HTML conversion engine. You see the "
    "ORIGINAL page (IMAGE 1) and OUR current render of it (IMAGE 2), plus our "
    "internal structure (the IR skeleton) and a catalog of override levers.\n\n"
    "Your job: emit the MINIMAL set of per-document OVERRIDES that would make our "
    "render's STRUCTURE match the original — correct reading order, figure "
    "membership, region classification, headings, table-vs-image. Do NOT fix "
    "intentional web transforms (single column, no page breaks, dropped link "
    "underlines, TOC removed) — those are correct.\n\n"
    "Return JSON: `overrides` (each {\"lever\": <one of the catalog names>, "
    "\"entry\": <the lever's config object ENCODED AS A JSON STRING>, \"why\": "
    "...}), `ops` (rare per-element edits, each a JSON-string edit object), "
    "and `residuals` (each {\"issue\": ..., \"missingLever\": <a short name for "
    "the capability we'd need>}). Prefer text-prefix matches; keep prefixes long "
    "enough to be unique. If our render already matches the original's structure, "
    "return empty arrays. Be conservative: never invent content, never reorder "
    "correct pages, propose the fewest entries that fix real structural defects."
)

# The API caps json_schema complexity, so `entry`/`op` are JSON-OBJECT-encoded
# STRINGS (parsed in prescribe()); apply-time (§4.2) validates each per lever.
_PRESCRIBE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "overrides": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "lever": {"type": "string", "enum": LEVER_NAMES},
                "entry": {"type": "string"},
                "why": {"type": "string"},
            },
            "required": ["lever", "entry"]}},
        "ops": {"type": "array", "items": {"type": "string"}},
        "residuals": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"issue": {"type": "string"},
                           "missingLever": {"type": "string"}},
            "required": ["issue", "missingLever"]}},
    },
    "required": ["overrides", "ops", "residuals"],
}


def _parse_entries(res):
    """Turn the model's JSON-string `entry`/`ops` back into dicts; drop
    unparseable ones (logged into residuals)."""
    good = []
    for ov in res.get("overrides", []):
        try:
            ov["entry"] = json.loads(ov["entry"]) if isinstance(ov.get("entry"), str) \
                else ov.get("entry")
            good.append(ov)
        except (json.JSONDecodeError, TypeError):
            res.setdefault("residuals", []).append(
                {"issue": f"unparseable entry for {ov.get('lever')}",
                 "missingLever": "prescriber-json"})
    res["overrides"] = good
    ops = []
    for op in res.get("ops", []):
        try:
            ops.append(json.loads(op) if isinstance(op, str) else op)
        except (json.JSONDecodeError, TypeError):
            pass
    res["ops"] = ops
    return res


def ir_skeleton(slug, page, limit=60):
    """One line per IR node on `page`: `{nid} p{page} {type} [l,b,r,t]: text`.
    The prescriber's map of what we currently produce."""
    ir_path = output_dir(slug) / "ir.json"
    if not ir_path.exists():
        return "(no IR)"
    ir = json.loads(ir_path.read_text())
    lines = []
    for n in irwalk.walk(ir.get("body", [])):
        if n.get("page") != page:
            continue
        bb = n.get("bbox") or [0, 0, 0, 0]
        txt = irwalk.subtree_text(n)[:limit] if not n.get("text") else n["text"][:limit]
        lines.append(f"{n.get('nid','?')} {n.get('type')} "
                     f"[{','.join(str(round(v)) for v in bb)}]: {txt}")
    return "\n".join(lines) or "(no nodes on this page)"


def prescribe(slug, page, our_png=None, model=None):
    """Vision prescription for one page (webified §4.1): returns
    {"overrides":[{lever,entry,why}], "ops":[...], "residuals":[{issue,missingLever}]}.
    Rejects+retries once on invalid JSON. Analysis-only — writes nothing (the
    §4.2 apply path, gated by safety rails, does the writing)."""
    orig = output_dir(slug) / "pages" / f"page-{page:04d}.png"
    if our_png is None:
        shots = shoot(slug, pages=[page])
        our_png = shots.get(page)
    if our_png is None or not Path(our_png).exists():
        return {"overrides": [], "ops": [],
                "residuals": [{"issue": "our render produced no content for this page",
                               "missingLever": "render-empty"}]}
    user = (f"IMAGE 1 is the ORIGINAL page {page}. IMAGE 2 is OUR render of that "
            f"page's content.\n\nOUR IR SKELETON (page {page}):\n{ir_skeleton(slug, page)}"
            f"\n\n{_LEVER_CATALOG}\n\nEmit the minimal overrides/ops that fix real "
            "structural mismatches; everything else → residuals.")
    for attempt in range(2):
        try:
            res = vision_json(_PRESCRIBE_SYSTEM, user, [orig, our_png],
                              _PRESCRIBE_SCHEMA, max_tokens=4000, model=model)
            res.setdefault("overrides", [])
            res.setdefault("ops", [])
            res.setdefault("residuals", [])
            return _parse_entries(res)
        except Exception as e:
            if attempt == 1:
                return {"overrides": [], "ops": [],
                        "residuals": [{"issue": f"prescribe failed: {e}",
                                       "missingLever": "prescriber-error"}]}
    return {"overrides": [], "ops": [], "residuals": []}
