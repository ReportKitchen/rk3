"""Playwright screenshotter for the webified loop (§0.8 recipe).

Four modes:
  --page N       crop to one original page's content (union bbox of the
                 [data-page="N"] elements — the same provenance visionqa uses)
  --selector CSS crop to a CSS selector (e.g. an nid element `#n4d9...`)
  --full         the whole rendered document
  --svg FILE     render a standalone SVG file to PNG (figure sidecar preview)

    python tools/shoot.py <slug> --page 15 [--out x.png]
    python tools/shoot.py <slug> --selector '[data-nid="n4d9..."]' [--out x.png]
    python tools/shoot.py <slug> --full [--out x.png]
    python tools/shoot.py --svg output/pdfium/<slug>/images/fig.svg [--out x.png]

Writes PNGs into output/pdfium/<slug>/qa/ by default (or --out). No other
side effects. Requires the rk3 service up on 127.0.0.1:8300 for doc modes.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rk3.documents import output_dir             # noqa: E402
from rk3.visionqa import _BBOX_JS, BASE          # noqa: E402  (reuse the bbox probe)


def _qa_out(slug, name):
    d = output_dir(slug) / "qa"
    d.mkdir(parents=True, exist_ok=True)
    return d / name


def _doc_url(slug):
    return f"{BASE}/output/pdfium/{slug}/index.html"


def shoot_page(slug, page, out=None, width=900):
    """Crop to page `page`'s content. Returns the PNG path (or None if the
    page has no rendered content)."""
    from playwright.sync_api import sync_playwright
    out = Path(out) if out else _qa_out(slug, f"shoot-page-{page:04d}.png")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": width, "height": 1400},
                              device_scale_factor=2)
        pg.goto(_doc_url(slug), wait_until="networkidle")
        box = pg.evaluate(_BBOX_JS, page)
        if not box:
            browser.close()
            return None
        pg.screenshot(path=str(out), clip=box, full_page=True)
        browser.close()
    return out


def shoot_selector(slug, selector, out=None, width=900):
    from playwright.sync_api import sync_playwright
    safe = selector.strip("#.[]").replace('"', "").replace("=", "-")[:40]
    out = Path(out) if out else _qa_out(slug, f"shoot-sel-{safe}.png")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": width, "height": 1400},
                              device_scale_factor=2)
        pg.goto(_doc_url(slug), wait_until="networkidle")
        el = pg.query_selector(selector)
        if el is None:
            browser.close()
            return None
        el.scroll_into_view_if_needed()
        el.screenshot(path=str(out))
        browser.close()
    return out


def shoot_full(slug, out=None, width=900):
    from playwright.sync_api import sync_playwright
    out = Path(out) if out else _qa_out(slug, "shoot-full.png")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": width, "height": 1400},
                              device_scale_factor=2)
        pg.goto(_doc_url(slug), wait_until="networkidle")
        pg.screenshot(path=str(out), full_page=True)
        browser.close()
    return out


def shoot_svg(svg_path, out=None):
    from playwright.sync_api import sync_playwright
    svg_path = Path(svg_path).resolve()
    out = Path(out) if out else svg_path.with_suffix(".png")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(device_scale_factor=2)
        pg.goto(f"file://{svg_path}", wait_until="networkidle")
        el = pg.query_selector("svg")
        (el.screenshot(path=str(out)) if el else pg.screenshot(path=str(out)))
        browser.close()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", nargs="?", help="document slug (omit for --svg)")
    ap.add_argument("--page", type=int)
    ap.add_argument("--selector")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--svg")
    ap.add_argument("--out")
    ap.add_argument("--width", type=int, default=900)
    a = ap.parse_args()

    if a.svg:
        res = shoot_svg(a.svg, a.out)
    elif a.page is not None:
        res = shoot_page(a.slug, a.page, a.out, a.width)
    elif a.selector:
        res = shoot_selector(a.slug, a.selector, a.out, a.width)
    elif a.full:
        res = shoot_full(a.slug, a.out, a.width)
    else:
        ap.error("pick a mode: --page N | --selector CSS | --full | --svg FILE")
    print(res if res else "(no content matched; nothing written)")


if __name__ == "__main__":
    main()
