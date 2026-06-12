"""Render stage: IR -> semantic HTML + 3 CSS layers + reconstructed nav.

Engine-agnostic: consumes ir.json only. Every element carries data-rk (debug
log key) and data-page (source page) plus any other provenance under data-*.
"""

import html
import shutil
from pathlib import Path

VERSION = 3

ASSETS = Path(__file__).parent / "assets"
CSS_FILES = ["layout.css", "default.css", "original.css"]


def run(ctx):
    ir = ctx.artifact("analyze")

    for css in CSS_FILES:
        shutil.copy(ASSETS / css, ctx.outdir / css)

    pages = ir.get("pages", {})
    parts = []
    for node in ir["body"]:
        parts.append(_render_node(ctx, node, pages))

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


def _render_node(ctx, node, pages):
    t = node["type"]
    if t == "heading":
        lv = min(max(node["level"], 1), 6)
        return (f'<h{lv} {_attrs(node, pages, {"id": node["id"]})}>'
                f'{html.escape(node["text"])}</h{lv}>')
    if t == "list":
        items = "\n".join(f"  <li>{html.escape(i)}</li>" for i in node["items"])
        return f'<ul {_attrs(node, pages)}>\n{items}\n</ul>'
    if t == "paragraph":
        body = html.escape(node["text"])
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
        children = "\n".join(_render_node(ctx, c, pages) for c in node["children"])
        return f'<aside {_attrs(node, pages)}>\n{children}\n</aside>'
    ctx.log.entry("unknown-node", type=t, rk=node.get("rk"))
    return f"<!-- unrendered node type {html.escape(t)} ({node.get('rk')}) -->"


def _render_nav(ir):
    heads = [n for n in ir["body"] if n["type"] == "heading" and n["level"] <= 3]
    if len(heads) < 2:
        return "<!-- nav omitted: fewer than 2 headings -->"
    items = "\n".join(
        f'  <li class="nav-l{h["level"]}"><a href="#{h["id"]}">{html.escape(h["text"])}</a></li>'
        for h in heads)
    return f'<nav aria-label="Document outline">\n<ul>\n{items}\n</ul>\n</nav>'
