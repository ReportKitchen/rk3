"""Render stage: IR -> semantic HTML + 3 CSS layers + reconstructed nav.

Engine-agnostic: consumes ir.json only. Every element carries data-rk (debug
log key) and data-page (source page) plus any other provenance under data-*.
"""

import html
import re
import shutil
from pathlib import Path

VERSION = 22

# ; and , are legal in URLs but in print they overwhelmingly join citations,
# so they terminate a match
URL_RE = re.compile(r'(?:https?://|www\.|doi\.org/)[^\s<>",;]+')
# a token that can plausibly continue a line-wrapped URL: path charset, and
# not a plain alphabetic word (which would be prose after the URL)
URL_CONT_RE = re.compile(r'[A-Za-z0-9._~%/#?=&+\-]+')

ASSETS = Path(__file__).parent / "assets"
CSS_FILES = ["layout.css", "default.css", "original.css"]


def run(ctx):
    ir = ctx.artifact("analyze")

    # layers 1+2 are static; layer 3 is generated per document from the
    # style provenance carried in the IR
    shutil.copy(ASSETS / "layout.css", ctx.outdir / "layout.css")
    shutil.copy(ASSETS / "default.css", ctx.outdir / "default.css")
    (ctx.outdir / "original.css").write_text(_original_css(ctx, ir),
                                             encoding="utf-8")

    pages = ir.get("pages", {})
    # footnote numbers that actually have note text; in-text refs only become
    # anchors when the target exists
    state = {"fn_nums": {n["n"] for node in ir["body"] if node["type"] == "footnotes"
                         for n in node["notes"]},
             "ref_seq": {},
             "autolink": ctx.cfg["output"].get("autolinkUrls", True),
             "anchors": _anchor_targets(ir),
             "pageTargets": _page_targets(ir)}
    parts = []
    for node in ir["body"]:
        parts.append(_render_node(ctx, node, pages, state))

    nav = _render_nav(ir)
    title = html.escape(ir.get("title", "Document"))
    layers = ctx.cfg["output"].get("cssLayers", ["layout", "default", "original"])
    links = "\n".join(
        f'<link rel="stylesheet" href="{layer}.css" id="css-{layer}">'
        for layer in ("layout", "default", "original") if layer in layers)
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{links}
</head>
<body>
{nav}
<main>
<article>
{chr(10).join(parts)}
</article>
</main>
</body>
</html>
"""
    (ctx.outdir / "index.html").write_text(doc, encoding="utf-8")
    ctx.log.entry("rendered", nodes=len(ir["body"]), css=CSS_FILES)


def _norm_anchor(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _anchor_targets(ir):
    """Linkable in-document targets: headings (by id) and aside headlines
    (asides render with id=nid). Lets print-styled cross-references become
    working internal links."""
    targets = {}
    for n in ir["body"]:
        if n["type"] == "heading":
            targets[_norm_anchor(n["text"])] = (n["id"], n["page"])
        elif n["type"] == "aside":
            first = next((c.get("text") for c in n.get("children", [])
                          if c.get("text")), None)
            if first:
                targets.setdefault(_norm_anchor(first), (n["nid"], n["page"]))
    return targets


def _page_targets(ir):
    """First anchorable element on each page (heading id or aside nid), so
    internal destPage links can land somewhere real."""
    targets = {}
    for n in ir["body"]:
        if n["page"] in targets:
            continue
        if n["type"] == "heading":
            targets[n["page"]] = n["id"]
        elif n["type"] == "aside":
            targets[n["page"]] = n["nid"]
    return targets


def _attrs(node, pages, extra=None):
    a = {"data-rk": node["rk"], "data-page": node["page"]}
    if node.get("nid"):
        a["data-nid"] = node["nid"]
    # fractional vertical position of the element on its source page (0 = top),
    # used by the viewer for smooth sync-scroll against the page images
    dims = pages.get(str(node["page"]))
    if dims and node.get("bbox"):
        yf = (dims[1] - node["bbox"][3]) / dims[1]
        a["data-yf"] = round(min(max(yf, 0.0), 1.0), 4)
    for k, v in (node.get("data") or {}).items():
        a[f"data-{k}"] = v
    if extra:
        a.update(extra)
    return " ".join(f'{k}="{html.escape(str(v), quote=True)}"' for k, v in a.items())


def _render_node(ctx, node, pages, state):
    t = node["type"]
    if t == "heading":
        lv = min(max(node["level"], 1), 6)
        body = html.escape(node["text"])
        if node.get("sectionNum"):
            body = (f'<span class="section-number">{html.escape(node["sectionNum"])}'
                    f'</span> {body}')
        return (f'<h{lv} {_attrs(node, pages, {"id": node["id"]})}>'
                f'{body}</h{lv}>')
    if t == "list":
        items = "\n".join(f"  <li>{html.escape(i)}</li>" for i in node["items"])
        return f'<ul {_attrs(node, pages)}>\n{items}\n</ul>'
    if t == "paragraph":
        body = _inline(node["text"], node.get("links"), node.get("refs"), state,
                       breaks=node.get("breaks"))
        if node.get("strong"):
            body = f"<strong>{body}</strong>"
        if node.get("quoteOpen"):
            body = (f'<span class="quote-mark open" aria-hidden="true">'
                    f'{html.escape(node["quoteOpen"])}</span>{body}')
        if node.get("quoteClose"):
            body += (f'<span class="quote-mark close" aria-hidden="true">'
                     f'{html.escape(node["quoteClose"])}</span>')
        return f'<p {_attrs(node, pages)}>{body}</p>'
    if t == "figure":
        cap = (f'\n  <figcaption>{html.escape(node["caption"])}</figcaption>'
               if node.get("caption") else "")
        return (f'<figure {_attrs(node, pages)}>\n'
                f'  <img src="{node["src"]}" alt="{html.escape(node["alt"], quote=True)}"'
                f' width="{node["width"]}">{cap}\n</figure>')
    if t == "table":
        rows = node["rows"]
        head = ""
        body_rows = rows
        if node.get("header") and len(rows) > 1:
            head = ("<thead><tr>"
                    + "".join(f"<th>{html.escape(c)}</th>" for c in rows[0])
                    + "</tr></thead>\n")
            body_rows = rows[1:]
        body = "\n".join(
            "  <tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>"
            for r in body_rows)
        return (f'<figure class="table" {_attrs(node, pages)}>\n<table>\n'
                f'{head}<tbody>\n{body}\n</tbody>\n</table>\n</figure>')
    if t == "aside":
        children = "\n".join(_render_node(ctx, c, pages, state)
                             for c in node["children"])
        classes = []
        if node.get("quote"):
            classes.append("quote")
        if node.get("pullQuote"):
            classes.append("pull-quote")
        extra = {"id": node["nid"]}  # anchor target for internal cross-refs
        if classes:
            extra["class"] = " ".join(classes)
        if node.get("pullQuote"):
            # duplicated decoration: visible flourish, silent to screen readers
            extra["aria-hidden"] = "true"
        return f'<aside {_attrs(node, pages, extra)}>\n{children}\n</aside>'
    if t == "footnotes":
        items = []
        for note in node["notes"]:
            n = note["n"]
            back = (f' <a class="fn-back" href="#fnref-{n}-1" '
                    f'title="Back to reference {n} in the text" '
                    f'aria-label="Back to reference {n}">↩</a>'
                    if state["ref_seq"].get(n) else "")
            items.append(f'  <li id="fn-{n}" value="{n}" data-rk="{note["rk"]}">'
                         f'{_inline(note["text"], None, None, state)}{back}</li>')
        # documents that number notes i/ii/iii keep their roman markers
        roman = all(re.fullmatch(r"[ivxl]+", note.get("marker", "").lower())
                    for note in node["notes"]) if node["notes"] else False
        ol = '<ol style="list-style-type: lower-roman">' if roman else "<ol>"
        return (f'<section class="footnotes" {_attrs(node, pages)}>\n'
                f'{ol}\n' + "\n".join(items) + '\n</ol>\n</section>')
    ctx.log.entry("unknown-node", type=t, rk=node.get("rk"))
    return f"<!-- unrendered node type {html.escape(t)} ({node.get('rk')}) -->"


def _inline(text, links, refs, state, breaks=None):
    """Escape text while wrapping link ranges in <a> and footnote-reference
    ranges in <sup><a>. Overlapping ranges: first (by start) wins. `breaks`
    are offsets of join-spaces that render as <br> (intentional hard
    returns)."""
    merged_links = []
    for s, e, target in sorted(links or []):
        if merged_links and s - merged_links[-1][1] <= 1 \
                and merged_links[-1][2] == target:
            merged_links[-1][1] = e  # one link wrapped across a line split
        else:
            merged_links.append([s, e, target])
    events = [(s, e, "link", target) for s, e, target in merged_links]
    events += [(s, e, "ref", n) for s, e, n in (refs or [])]
    events += [(s, s + 1, "br", None) for s in (breaks or [])]
    if state.get("autolink"):
        events += _autolink_events(text, events)
    # superscript numbers often carry their own link annotation pointing at the
    # notes page; the footnote anchor is more useful, so a resolvable ref wins
    # ties, otherwise the link does
    events.sort(key=lambda ev: (
        ev[0], ev[1], 0 if ev[2] == "ref" and ev[3] in state["fn_nums"] else 1))
    out = []
    pos = 0
    for s, e, kind, payload in events:
        if s < pos or e > len(text):
            continue
        out.append(html.escape(text[pos:s]))
        seg = html.escape(text[s:e])
        if kind == "br":
            out.append("<br>\n")
            pos = e
            continue
        if kind == "link":
            uri = payload.get("uri")
            if payload.get("styled"):
                # print-styled cross-reference with no PDF target: if the text
                # names a heading/box in THIS document, link it for real;
                # otherwise keep it as a marked span (a dead <a> misleads)
                target = _resolve_anchor(text[s:e], state["anchors"])
                if target:
                    tid, tpage = target
                    out.append(f'<a href="#{tid}" data-link-styled="true" '
                               f'data-target-page="{tpage}">{seg}</a>')
                else:
                    out.append(f'<span data-link-styled="true">{seg}</span>')
            elif uri:
                href = uri if "://" in uri or uri.startswith(("mailto:", "#")) \
                    else "https://" + uri
                cls = ' class="autolink"' if payload.get("auto") else ""
                # when the anchor text IS the url, print wraps corrupt it
                # (underscores become spaces at line breaks): show the href
                raw = text[s:e]
                if raw.lstrip().lower().startswith(("http", "www.")) and \
                        _alnum_only(raw) == _alnum_only(href):
                    seg = html.escape(href)
                out.append(f'<a{cls} href="{html.escape(href, quote=True)}">{seg}</a>')
            else:
                dest = payload.get("destPage")
                tid = state["pageTargets"].get(dest) \
                    or next((state["pageTargets"][p]
                             for p in sorted(state["pageTargets"])
                             if p >= (dest or 0)), None)
                href = f' href="#{tid}"' if tid else ""
                out.append(f'<a{href} data-dest-page="{dest}" '
                           f'data-target-page="{dest}">{seg}</a>')
        elif payload in state["fn_nums"]:
            k = state["ref_seq"].get(payload, 0) + 1
            state["ref_seq"][payload] = k
            # spaces inside a marker are run-split artifacts ("i i" is ii)
            marker = seg.replace(" ", "")
            out.append(f'<sup class="fnref" id="fnref-{payload}-{k}">'
                       f'<a href="#fn-{payload}">{marker}</a></sup>')
            if e < len(text) and text[e].isalpha():
                out.append(" ")  # run splits often swallow the space after
        else:
            out.append(f"<sup>{seg.replace(' ', '')}</sup>")
            if e < len(text) and text[e].isalpha():
                out.append(" ")
        pos = e
    out.append(html.escape(text[pos:]))
    return "".join(out)


def _alnum_only(t):
    return re.sub(r"[^a-z0-9]+", "", (t or "").lower())


def _resolve_anchor(seg_text, targets):
    norm = _norm_anchor(re.sub(r"[,.;:]+\s*$", "", seg_text))
    if not norm or len(norm) < 8:
        return None
    if norm in targets:
        return targets[norm]
    hits = [v for k, v in targets.items()
            if k.startswith(norm) or norm.startswith(k)]
    return hits[0] if len(hits) == 1 else None


def _autolink_events(text, events):
    """Plain-text URLs/DOIs in the gaps between explicit ranges become links
    (config: output.autolinkUrls). URLs line-wrapped in the source PDF arrive
    with an interior space; bridge across it when the next token is path-like
    rather than prose. Display text keeps the space; the href drops it."""
    occupied = [(s, e) for s, e, *_ in events]
    found = []
    for m in URL_RE.finditer(text):
        s, e = m.start(), m.end()
        while e < len(text) and text[e] == " ":
            m2 = URL_CONT_RE.match(text, e + 1)
            # continuation must look like a path fragment (digits, slashes…),
            # not prose or an initial like "D."
            if not m2 or not re.search(r"[\d/=#?%&]", m2.group(0)):
                break
            e = m2.end()
        while e > s and text[e - 1] in ".,;:!?'\")]}":
            e -= 1
        if e <= s or any(not (e <= os or s >= oe) for os, oe in occupied):
            continue
        found.append((s, e, "link",
                      {"uri": text[s:e].replace(" ", ""), "auto": True}))
    return found


SERIF_HINTS = ("serif", "georgia", "times", "garamond", "minion", "caslon",
               "baskerville", "palatino", "charter", "utopia", "didot", "bodoni")

MARKER_STYLE = {"•": "disc", "◦": "circle", "·": "disc"}


def _font_css(name):
    """'ANGKGH+Helvetica-Bold' -> ('Helvetica', 'sans-serif', 700, None)."""
    name = re.sub(r"^[A-Z]{6}\+", "", name or "")
    low = name.lower()
    base = name.split("-")[0].split(",")[0]
    family = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base).strip()
    weight = None
    if "black" in low or "heavy" in low:
        weight = 800
    elif "semibold" in low or "demi" in low:
        weight = 600
    elif "bold" in low:
        weight = 700
    elif "medium" in low:
        weight = 500
    elif "light" in low or low.endswith("-boo") or "book" in low:
        weight = 400 if "book" in low or low.endswith("-boo") else 300
    style = "italic" if ("italic" in low or "oblique" in low) else None
    generic = "serif" if any(h in low for h in SERIF_HINTS) else "sans-serif"
    return family, generic, weight, style


def _usable_color(hex_color):
    """Colors that work on our white page: skip near-white text colors (they
    were legible only on the PDF's dark backgrounds)."""
    if not hex_color:
        return None
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return None if min(r, g, b) > 225 else hex_color


def _style_profile(ir):
    fresh = lambda: {"font": None, "color": None, "size": None,
                     "_f": {}, "_c": {}, "_s": {}}
    body = fresh()
    heads = {}

    def feed(node):
        d = node.get("data") or {}
        w = max(len(node.get("text", "") or ""), 1)
        if node["type"] == "paragraph" and "fill" not in d:
            tgt = body
        elif node["type"] == "heading":
            tgt = heads.setdefault(node["level"], fresh())
        else:
            return
        for key, bucket in (("font", "_f"), ("color", "_c"), ("size", "_s")):
            v = d.get(key)
            if v is not None:
                tgt[bucket][v] = tgt[bucket].get(v, 0) + w

    for n in ir["body"]:
        feed(n)
        for c in n.get("children", []):
            feed(c)

    for tgt in (body, *heads.values()):
        for key, bucket in (("font", "_f"), ("color", "_c"), ("size", "_s")):
            if tgt[bucket]:
                tgt[key] = max(tgt[bucket], key=tgt[bucket].get)
    return body, heads


def _original_css(ctx, ir):
    """Layer 3: best-effort recreation of the source document's look, built
    entirely from IR provenance. Regenerated on every render."""
    body, heads = _style_profile(ir)
    body_pt = body["size"] or 10.0
    out = ["/* Layer 3 — original-look styling, generated per document from",
           "   extraction provenance (fonts, colors, sizes). Do not edit:",
           "   regenerated by the render stage. */", ""]

    if body["font"] or body["color"]:
        fam, generic, weight, style = _font_css(body["font"] or "")
        rules = []
        if fam:
            rules.append(f'  font-family: "{fam}", {generic};')
        body_color = _usable_color(body["color"])
        if body_color:
            rules.append(f"  color: {body_color};")
        out += ["body {", *rules, "}", ""]

    accent = None
    for lv in sorted(heads):
        h = heads[lv]
        rules = []
        if h["font"]:
            fam, generic, weight, style = _font_css(h["font"])
            rules.append(f'  font-family: "{fam}", {generic};')
            if weight:
                rules.append(f"  font-weight: {weight};")
            if style:
                rules.append(f"  font-style: {style};")
        h_color = _usable_color(h["color"])
        if h_color:
            rules.append(f"  color: {h_color};")
            if accent is None and max(int(h_color[i:i + 2], 16)
                                      for i in (1, 3, 5)) > 80:
                accent = h_color  # first non-black usable heading color
        if h["size"]:
            rules.append(f"  font-size: {round(h['size'] / body_pt, 2)}rem;")
        if rules:
            out += [f"h{min(lv, 6)} {{", *rules, "}", ""]

    # callout boxes keep their original fill/border and (when narrower than
    # the column) their floated position and width
    body_color = body["color"]
    for n in ir["body"]:
        d = n.get("data") or {}
        if n["type"] == "heading":
            # heading whose own color differs from its level's dominant color
            lv_color = heads.get(n["level"], {}).get("color")
            own = _usable_color(d.get("color"))
            if own and lv_color and own != lv_color:
                out += [f'[data-nid="{n["nid"]}"] {{ color: {own}; }}', ""]
        if n["type"] != "aside":
            continue
        # per-child exceptions: colors/sizes that differ from body text
        for c in n.get("children", []):
            cd = c.get("data") or {}
            crules = []
            own = _usable_color(cd.get("color"))
            if own and own != body_color:
                crules.append(f"  color: {own};")
            if cd.get("size") and abs(cd["size"] / body_pt - 1) >= 0.12:
                crules.append(f"  font-size: {round(cd['size'] / body_pt, 2)}em;")
            if crules:
                out += [f'[data-nid="{c["nid"]}"] {{', *crules, "}", ""]
        rules = []
        if d.get("fill") and d["fill"] not in ("#ffffff",):
            rules.append(f"  background: {d['fill']};")
        else:
            # no fill in the original: the box sits on the page background
            rules.append("  background: transparent;")
        if n.get("borders"):
            rules.append("  border: none;")
            for side, spec in sorted(n["borders"].items()):
                px = round(spec["width"] * 4 / 3)
                rules.append(f"  border-{side}: {px}px solid {spec['color']};")
        elif d.get("stroke"):
            rules.append(f"  border: 1px solid {d['stroke']};")
        elif d.get("fill"):
            rules.append("  border: none;")
        lay = n.get("layout")
        if lay:
            pct = round(lay["widthFrac"] * 100)
            side = lay["anchor"]
            margin = ("0 0 1rem 1.5rem" if side == "right" else "0 1.5rem 1rem 0")
            rules += [f"  float: {side};", f"  width: {pct}%;",
                      f"  margin: {margin};"]
        if rules:
            out += [f'aside[data-nid="{n["nid"]}"] {{', *rules, "}", ""]

    # original list markers (symbol-font glyphs approximate to square)
    markers = {(n.get("data") or {}).get("marker")
               for n in ir["body"] if n["type"] == "list"}
    for n in ir["body"]:
        for c in n.get("children", []):
            if c["type"] == "list":
                markers.add((c.get("data") or {}).get("marker"))
    for m in sorted(filter(None, markers)):
        style_name = MARKER_STYLE.get(m, "square")
        if style_name != "disc":
            out += [f'ul[data-marker="{html.escape(m)}"] '
                    f'{{ list-style-type: {style_name}; }}', ""]

    if accent:
        out += [".section-number {",
                "  display: inline-grid;",
                "  place-items: center;",
                "  min-width: 1.6em;",
                "  height: 1.6em;",
                f"  background: {accent};",
                "  color: #fff;",
                "  border-radius: 50%;",
                "  font-size: 0.7em;",
                "  vertical-align: 0.2em;",
                "}", ""]

    out += ["aside.quote { position: relative; padding-left: 2.5rem; }",
            "aside.quote .quote-mark {",
            "  position: absolute;",
            "  left: 0.5rem;",
            "  top: 0.25rem;",
            f"  color: {accent or '#999'};",
            "  font-size: 2.6em;",
            "  line-height: 1;",
            "  opacity: 0.6;",
            "}",
            "aside.quote .quote-mark.close { display: none; }", ""]

    return "\n".join(out)


def _render_nav(ir):
    heads = [n for n in ir["body"] if n["type"] == "heading" and n["level"] <= 3]
    if len(heads) < 2:
        return "<!-- nav omitted: fewer than 2 headings -->"
    items = "\n".join(
        f'  <li class="nav-l{h["level"]}"><a href="#{h["id"]}">{html.escape(h["text"])}</a></li>'
        for h in heads)
    return f'<nav aria-label="Document outline">\n<ul>\n{items}\n</ul>\n</nav>'
