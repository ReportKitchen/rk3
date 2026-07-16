"""Scan a live web page for the style of its main body content.

Given a URL (typically the client's own page for the report we've converted),
render it in a headless browser and read back the *computed* style of the
element that holds the main body text — background, font, weight, colours, link
colours (incl. hover), the readable measure — plus page background and a
sidebar/offset read of the layout.

Why a browser and not an HTML parse: the values we want are the result of the
full CSS cascade (external sheets, web fonts, JS-applied styles). Only a real
render exposes them, via `getComputedStyle`. Main-text locators (trafilatura,
readability) find the content *text* but hand back cleaned HTML detached from
the live DOM, so they can't report the live node's computed style — we locate
the node ourselves, in-page, and measure it directly.

The output is deliberately tool-agnostic (a `PageStyle` dict): Landing Page
Maker maps it to its theme, but RK Express or any other tool can consume the
same shape. Mapping to a specific theme lives with that tool, not here.

Entry point: `scan_page(url) -> dict`. Also runnable as
`python -m rk3.webscan <url> [--shot out.png]`.
"""

from __future__ import annotations

import json
import sys

# Everything measurable in one pass, in the page's own context. Returns a plain
# dict (JSON-able). Nodes we may need to interact with afterwards (the link, for
# its :hover colour) are tagged with data-rk-scan so Playwright can re-find them.
_EXTRACT_JS = r"""
() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const cs = el => getComputedStyle(el);
  const rnd = n => Math.round(n);

  // rgb()/rgba() -> #rrggbb; null when fully transparent (so callers can climb)
  const toHex = c => {
    if (!c) return null;
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return c === 'transparent' ? null : c;
    const p = m[1].split(',').map(s => s.trim());
    const r = +p[0], g = +p[1], b = +p[2], a = p.length > 3 ? +p[3] : 1;
    if (a === 0) return null;
    const h = n => Math.max(0, Math.min(255, n)).toString(16).padStart(2, '0');
    return '#' + h(r) + h(g) + h(b);
  };

  const vis = el => {
    const s = cs(el);
    if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 1 && r.height > 1;
  };
  const txt = el => (el.innerText || '').trim();

  // the effective background behind an element: climb until a non-transparent
  // background-color is found (backgrounds are usually set on an ancestor)
  const effBg = el => {
    let e = el;
    while (e && e !== document.documentElement) {
      const c = toHex(cs(e).backgroundColor);
      if (c) return c;
      e = e.parentElement;
    }
    return toHex(cs(document.documentElement).backgroundColor) || '#ffffff';
  };

  const box = el => {
    const r = el.getBoundingClientRect();
    return { x: rnd(r.x), y: rnd(r.y), w: rnd(r.width), h: rnd(r.height) };
  };
  const primaryFont = stack =>
    (stack || '').split(',')[0].trim().replace(/^["']|["']$/g, '');

  // --- 1. locate the main content: the element maximising the length of body
  // text (<p>) it contains. Each substantial paragraph credits its ancestors;
  // the highest-scoring ancestor is the content container. ------------------
  const paras = [...document.querySelectorAll('p')]
    .filter(p => vis(p) && txt(p).length >= 40);
  const score = new Map();
  for (const p of paras) {
    const len = txt(p).length;
    let e = p.parentElement, depth = 0;
    while (e && depth < 6) {
      score.set(e, (score.get(e) || 0) + len);
      e = e.parentElement;
      depth++;
    }
  }
  let content = document.body, best = 0;
  for (const [el, s] of score) if (s > best) { best = s; content = el; }

  // representative paragraph = the longest visible <p> in the content
  const inside = [...content.querySelectorAll('p')]
    .filter(p => vis(p) && txt(p).length >= 40)
    .sort((a, b) => txt(b).length - txt(a).length);
  const para = inside[0] || content;

  // The text *column*, derived without guessing a wrapper-width ratio: a body
  // <p> fills its column, so the paragraphs give the column's true horizontal
  // extent (x + width) — which is what "centered vs offset, sidebar or not" is
  // about — while the paragraph-dense wrapper gives the vertical extent (so a
  // sidebar is compared over the column's whole height). Using the *widest*
  // substantial paragraph guards against a lone narrow/floated one.
  const rects = inside.map(p => p.getBoundingClientRect());
  const colW = rects.length ? Math.max(...rects.map(r => r.width)) : para.getBoundingClientRect().width;
  const colX = rects.length
    ? rects.reduce((a, b) => (b.width > a.width ? b : a)).x
    : para.getBoundingClientRect().x;
  const wrapBox = content.getBoundingClientRect();
  const cbox = { x: rnd(colX), y: rnd(wrapBox.y), w: rnd(colW), h: rnd(wrapBox.height) };

  // representative heading = the largest visible h1-h3 *inside* the content. No
  // document-wide fallback: a global h1 is usually the site/hero title (often
  // white-on-dark), which would report a misleading heading colour.
  const heads = [...content.querySelectorAll('h1,h2,h3')]
    .filter(vis)
    .sort((a, b) => parseFloat(cs(b).fontSize) - parseFloat(cs(a).fontSize));
  const head = heads[0] || null;

  // representative link = one inside the body text if possible
  let link = para.querySelector('a');
  if (!link || !vis(link)) link = [...content.querySelectorAll('a')].filter(vis)[0] || null;

  content.setAttribute('data-rk-scan', 'content');
  para.setAttribute('data-rk-scan', 'para');
  if (head) head.setAttribute('data-rk-scan', 'head');
  if (link) link.setAttribute('data-rk-scan', 'link');

  const pStyle = cs(para);
  const pbox = box(para);

  // --- 2. page background: the full-bleed area around the column. Climb to the
  // first ancestor spanning ~the viewport, and read its effective background. --
  let wide = content;
  while (wide.parentElement && wide.getBoundingClientRect().width < vw * 0.9) {
    wide = wide.parentElement;
  }

  // --- 3. sidebar / offset: block elements beside the content column that
  // overlap it vertically. A real sidebar sits entirely left or right of the
  // column, is a sensible width, and carries content. Exclude relative to the
  // paragraph (not the wrapper) — a two-column page's sidebar is a *sibling* of
  // the column but a descendant of the wrapper, so excluding by the wrapper
  // hides it; the paragraph is inside the column and never inside the sidebar.
  const cTop = cbox.y, cBot = cbox.y + cbox.h;
  const related = (a, b) => a === b || a.contains(b) || b.contains(a);
  const sides = { left: null, right: null };
  for (const el of document.body.querySelectorAll('*')) {
    if (related(el, para) || !vis(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 120 || r.width > vw * 0.5) continue;
    if (r.height < cbox.h * 0.25) continue;
    if (txt(el).length < 20) continue;
    const overlap = Math.min(cBot, r.bottom) - Math.max(cTop, r.top);
    if (overlap < cbox.h * 0.3) continue;
    let where = null;
    if (r.right <= cbox.x + 8) where = 'left';
    else if (r.left >= cbox.x + cbox.w - 8) where = 'right';
    if (!where) continue;
    const prev = sides[where];
    if (!prev || r.width * r.height > prev._area) {
      sides[where] = { x: rnd(r.x), y: rnd(r.y), w: rnd(r.width), h: rnd(r.height), _area: r.width * r.height };
    }
  }
  for (const k of ['left', 'right']) if (sides[k]) delete sides[k]._area;

  const leftGap = cbox.x, rightGap = vw - (cbox.x + cbox.w);
  let align;
  if (sides.left && !sides.right) align = 'right';        // pushed right by a left sidebar
  else if (sides.right && !sides.left) align = 'left';
  else if (Math.abs(leftGap - rightGap) <= vw * 0.12) align = 'center';
  else align = leftGap > rightGap ? 'right' : 'left';

  return {
    content: {
      bg: effBg(para),
      width: pbox.w,                 // the readable measure (body-text column)
      containerWidth: cbox.w,
      font: primaryFont(pStyle.fontFamily),
      fontStack: pStyle.fontFamily,
      fontSize: rnd(parseFloat(pStyle.fontSize)),
      lineHeight: pStyle.lineHeight,
      textColor: toHex(pStyle.color),
      textWeight: +pStyle.fontWeight,
      link: link ? { color: toHex(cs(link).color), hover: null } : null,
      heading: head ? {
        color: toHex(cs(head).color),
        font: primaryFont(cs(head).fontFamily),
        fontStack: cs(head).fontFamily,
        weight: +cs(head).fontWeight,
        size: rnd(parseFloat(cs(head).fontSize)),
      } : null,
    },
    page: { bg: effBg(wide) },
    layout: {
      viewport: { w: vw, h: vh },
      contentBox: cbox,
      paraBox: pbox,
      leftGap: rnd(leftGap),
      rightGap: rnd(rightGap),
      align,
      sidebar: (sides.left || sides.right)
        ? { present: true, side: sides.left ? 'left' : 'right', box: sides.left || sides.right }
        : { present: false },
    },
    diagnostics: {
      paragraphs: paras.length,
      bodyChars: best,
      wrapperTag: content.tagName.toLowerCase(),
      wrapperClass: (typeof content.className === 'string' ? content.className : '') || null,
    },
  };
}
"""

# a plain desktop UA that names us — the owner directed the scan, so we identify
# rather than masquerade
_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
       "Chrome/125.0 Safari/537.36 ReportKitchen-PageScan/1.0")


def scan_page(url: str, *, timeout_ms: int = 30000,
              viewport: tuple[int, int] = (1280, 2200),
              shot_path: str | None = None,
              regions_dir: str | None = None) -> dict:
    """Render `url` and return a tool-agnostic PageStyle dict.

    `regions_dir`, when set, also writes `header.png`, `sidebar.png` and
    `footer.png` there — the page chrome around the content column, cropped from
    the same render — and records their geometry under `result["regions"]`.
    These are the raw material for ghosted overlays on a builder canvas.

    Robots are intentionally not consulted: this runs only against a URL the
    content owner supplied for their own report. Sync Playwright — call from a
    worker thread if invoking under an async server.
    """
    from playwright.sync_api import sync_playwright

    result: dict = {"url": url, "ok": False}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": viewport[0], "height": viewport[1]},
            user_agent=_UA,
        )
        try:
            page.goto(url, wait_until="load", timeout=timeout_ms)
            # let web fonts settle so font-family/weight reflect the real face
            page.evaluate("document.fonts ? document.fonts.ready.then(() => true) : true")
            page.wait_for_timeout(600)

            data = page.evaluate(_EXTRACT_JS)

            # link :hover colour needs a real hover — read the tagged link before
            # and after. Many sites only change the underline, leaving colour put.
            link = data.get("content", {}).get("link")
            if link:
                loc = page.locator('[data-rk-scan="link"]').first
                try:
                    loc.hover(timeout=2000)
                    page.wait_for_timeout(150)
                    hover = loc.evaluate("el => getComputedStyle(el).color")
                    link["hover"] = _rgb_to_hex(hover) or link["color"]
                except Exception:
                    link["hover"] = link["color"]

            if shot_path:
                page.screenshot(path=shot_path, full_page=True)

            if regions_dir:
                data["regions"] = _capture_regions(page, data, regions_dir)

            result.update(data)
            result["ok"] = True
        except Exception as e:  # surface, never swallow (repo posture)
            result["error"] = f"{type(e).__name__}: {e}"
        finally:
            browser.close()
    return result


def _capture_regions(page, data: dict, out_dir: str) -> dict:
    """Clip the page chrome around the content column: header (above), sidebar
    (the detected rail), footer (below). Same render as the scan, so free."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    lay = data["layout"]
    vw = lay["viewport"]["w"]
    cb = lay["contentBox"]
    page_h = page.evaluate(
        "Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
    out: dict = {}

    def clip(name, box):
        if box["width"] < 8 or box["height"] < 8:
            return
        path = os.path.join(out_dir, f"{name}.png")
        page.screenshot(path=path, clip=box)
        out[name] = {"path": path, "box": {k: round(v) for k, v in box.items()}}

    clip("header", {"x": 0, "y": 0, "width": vw, "height": cb["y"]})
    sb = lay["sidebar"]
    if sb.get("present"):
        s = sb["box"]
        clip("sidebar", {"x": s["x"], "y": s["y"], "width": s["w"], "height": s["h"]})
    bottom = cb["y"] + cb["h"]
    clip("footer", {"x": 0, "y": bottom, "width": vw, "height": min(page_h - bottom, 1600)})
    return out


def _rgb_to_hex(c: str | None) -> str | None:
    if not c:
        return None
    import re
    m = re.match(r"rgba?\(([^)]+)\)", c)
    if not m:
        return None if c == "transparent" else c
    parts = [s.strip() for s in m.group(1).split(",")]
    r, g, b = int(float(parts[0])), int(float(parts[1])), int(float(parts[2]))
    a = float(parts[3]) if len(parts) > 3 else 1.0
    if a == 0:
        return None
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("usage: python -m rk3.webscan <url> [--shot out.png]", file=sys.stderr)
        raise SystemExit(2)
    url = args[0]
    shot = args[args.index("--shot") + 1] if "--shot" in args else None
    regions = args[args.index("--regions") + 1] if "--regions" in args else None
    print(json.dumps(scan_page(url, shot_path=shot, regions_dir=regions),
                     indent=2, ensure_ascii=False))
