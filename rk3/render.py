"""Render stage: IR -> semantic HTML + 3 CSS layers + reconstructed nav.

Engine-agnostic: consumes ir.json only. Every element carries data-rk (debug
log key) and data-page (source page) plus any other provenance under data-*.
"""

import html
import re
import shutil
from pathlib import Path

VERSION = 11

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

    for css in CSS_FILES:
        shutil.copy(ASSETS / css, ctx.outdir / css)

    pages = ir.get("pages", {})
    # footnote numbers that actually have note text; in-text refs only become
    # anchors when the target exists
    state = {"fn_nums": {n["n"] for node in ir["body"] if node["type"] == "footnotes"
                         for n in node["notes"]},
             "ref_seq": {},
             "autolink": ctx.cfg["output"].get("autolinkUrls", True)}
    parts = []
    for node in ir["body"]:
        parts.append(_render_node(ctx, node, pages, state))

    nav = _render_nav(ir)
    title = html.escape(ir.get("title", "Document"))
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="layout.css" id="css-layout">
<link rel="stylesheet" href="default.css" id="css-default">
<link rel="stylesheet" href="original.css" id="css-original">
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
        return (f'<h{lv} {_attrs(node, pages, {"id": node["id"]})}>'
                f'{html.escape(node["text"])}</h{lv}>')
    if t == "list":
        items = "\n".join(f"  <li>{html.escape(i)}</li>" for i in node["items"])
        return f'<ul {_attrs(node, pages)}>\n{items}\n</ul>'
    if t == "paragraph":
        body = _inline(node["text"], node.get("links"), node.get("refs"), state)
        if node.get("strong"):
            body = f"<strong>{body}</strong>"
        return f'<p {_attrs(node, pages)}>{body}</p>'
    if t == "figure":
        cap = (f'\n  <figcaption>{html.escape(node["caption"])}</figcaption>'
               if node.get("caption") else "")
        return (f'<figure {_attrs(node, pages)}>\n'
                f'  <img src="{node["src"]}" alt="{html.escape(node["alt"], quote=True)}"'
                f' width="{node["width"]}">{cap}\n</figure>')
    if t == "aside":
        children = "\n".join(_render_node(ctx, c, pages, state)
                             for c in node["children"])
        return f'<aside {_attrs(node, pages)}>\n{children}\n</aside>'
    if t == "footnotes":
        items = []
        for note in node["notes"]:
            n = note["n"]
            back = (f' <a class="fn-back" href="#fnref-{n}-1" '
                    f'aria-label="Back to reference {n}">↩</a>'
                    if state["ref_seq"].get(n) else "")
            items.append(f'  <li id="fn-{n}" value="{n}" data-rk="{note["rk"]}">'
                         f'{_inline(note["text"], None, None, state)}{back}</li>')
        return (f'<section class="footnotes" {_attrs(node, pages)}>\n'
                f'<ol>\n' + "\n".join(items) + '\n</ol>\n</section>')
    ctx.log.entry("unknown-node", type=t, rk=node.get("rk"))
    return f"<!-- unrendered node type {html.escape(t)} ({node.get('rk')}) -->"


def _inline(text, links, refs, state):
    """Escape text while wrapping link ranges in <a> and footnote-reference
    ranges in <sup><a>. Overlapping ranges: first (by start) wins."""
    events = [(s, e, "link", target) for s, e, target in (links or [])]
    events += [(s, e, "ref", n) for s, e, n in (refs or [])]
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
        if kind == "link":
            uri = payload.get("uri")
            if payload.get("styled"):
                # colored like the document's links but has no target in the
                # PDF (print-styled cross-reference) — not rendered as <a>,
                # since a link that goes nowhere misleads; provenance kept
                out.append(f'<span data-link-styled="true">{seg}</span>')
            elif uri:
                href = uri if "://" in uri or uri.startswith(("mailto:", "#")) \
                    else "https://" + uri
                cls = ' class="autolink"' if payload.get("auto") else ""
                out.append(f'<a{cls} href="{html.escape(href, quote=True)}">{seg}</a>')
            else:
                out.append(f'<a data-dest-page="{payload.get("destPage")}">{seg}</a>')
        elif payload in state["fn_nums"]:
            k = state["ref_seq"].get(payload, 0) + 1
            state["ref_seq"][payload] = k
            out.append(f'<sup class="fnref" id="fnref-{payload}-{k}">'
                       f'<a href="#fn-{payload}">{seg}</a></sup>')
        else:
            out.append(f"<sup>{seg}</sup>")
        pos = e
    out.append(html.escape(text[pos:]))
    return "".join(out)


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


def _render_nav(ir):
    heads = [n for n in ir["body"] if n["type"] == "heading" and n["level"] <= 3]
    if len(heads) < 2:
        return "<!-- nav omitted: fewer than 2 headings -->"
    items = "\n".join(
        f'  <li class="nav-l{h["level"]}"><a href="#{h["id"]}">{html.escape(h["text"])}</a></li>'
        for h in heads)
    return f'<nav aria-label="Document outline">\n<ul>\n{items}\n</ul>\n</nav>'
