"""Render stage: IR -> semantic HTML + 3 CSS layers + reconstructed nav.

Engine-agnostic: consumes ir.json only. Every element carries data-rk (debug
log key) and data-page (source page) plus any other provenance under data-*.
"""

import html
import shutil
from pathlib import Path

VERSION = 1

ASSETS = Path(__file__).parent / "assets"
CSS_FILES = ["layout.css", "default.css", "original.css"]


def run(ctx):
    ir = ctx.artifact("analyze")

    for css in CSS_FILES:
        shutil.copy(ASSETS / css, ctx.outdir / css)

    parts = []
    for node in ir["body"]:
        parts.append(_render_node(ctx, node))

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


def _attrs(node, extra=None):
    a = {"data-rk": node["rk"], "data-page": node["page"]}
    for k, v in (node.get("data") or {}).items():
        a[f"data-{k}"] = v
    if extra:
        a.update(extra)
    return " ".join(f'{k}="{html.escape(str(v), quote=True)}"' for k, v in a.items())


def _render_node(ctx, node):
    t = node["type"]
    if t == "heading":
        lv = min(max(node["level"], 1), 6)
        return (f'<h{lv} {_attrs(node, {"id": node["id"]})}>'
                f'{html.escape(node["text"])}</h{lv}>')
    if t == "list":
        items = "\n".join(f"  <li>{html.escape(i)}</li>" for i in node["items"])
        return f'<ul {_attrs(node)}>\n{items}\n</ul>'
    if t == "paragraph":
        return f'<p {_attrs(node)}>{html.escape(node["text"])}</p>'
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
