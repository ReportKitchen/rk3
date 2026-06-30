"""Vision-QA reviewer (analysis-only).

Screenshots our rendered output, cropped per ORIGINAL page via the `data-page`
provenance, and asks a vision model to flag discrepancies against the original
page image. It is a REVIEWER — it flags, it never edits. The conversion rubric
is injected so the model tells an intentional transform (single column, no page
breaks, dropped underlines …) from a real error.
"""

from pathlib import Path

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
                    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                    "where": {"type": "string"},
                    "issue": {"type": "string"},
                },
                "required": ["category", "severity", "where", "issue"],
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
    "CRITICAL: use the conversion rubric below to distinguish an INTENTIONAL TRANSFORM "
    "(e.g. single column, no page breaks, dropped link underlines, TOC removed) — which "
    "you must NOT flag — from a real ERROR (lost content, wrong reading order, dropped "
    "emphasis, broken link, mis-spaced words like 'b y', content in the wrong container, "
    "a heading missed or mis-leveled, a figure/table dropped). Only flag real errors. If "
    "the conversion is faithful, return an empty list. Be specific and locatable. You are "
    "a REVIEWER, not an editor — never rewrite content, only describe what is wrong."
)


def _system():
    rubric = RUBRIC.read_text() if RUBRIC.exists() else "(rubric not found)"
    return f"{_BASE_SYSTEM}\n\n=== CONVERSION RUBRIC ===\n{rubric}"


def qa_page(slug, page, our_png=None):
    """Flag discrepancies for one page (image-vs-image). Returns the flags list."""
    orig = output_dir(slug) / "pages" / f"page-{page:04d}.png"
    if our_png is None:
        our_png = output_dir(slug) / "qa" / f"our-page-{page:04d}.png"
    user = ("IMAGE 1 is the ORIGINAL page. IMAGE 2 is OUR conversion of that page's "
            "content (reflowed to a single web column). Flag only real discrepancies, "
            "per the rubric — intentional transforms are not errors.")
    res = vision_json(_system(), user, [orig, our_png], _SCHEMA, max_tokens=4000)
    return res.get("flags", [])
