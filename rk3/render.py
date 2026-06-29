"""Render stage: IR -> semantic HTML + 3 CSS layers + reconstructed nav.

Engine-agnostic: consumes ir.json only. Every element carries data-rk (debug
log key) and data-page (source page) plus any other provenance under data-*.
"""

import html
import re
import shutil
from collections import Counter
from pathlib import Path

VERSION = 49

OL_TYPE = {"lower-alpha": "a", "upper-alpha": "A"}

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
    _apply_ops(ctx, ir)

    # layers 1+2 are static; layer 3 is generated per document from the
    # style provenance carried in the IR
    shutil.copy(ASSETS / "layout.css", ctx.outdir / "layout.css")
    shutil.copy(ASSETS / "default.css", ctx.outdir / "default.css")
    (ctx.outdir / "original.css").write_text(_original_css(ctx, ir),
                                             encoding="utf-8")
    # embed.css: the @font-face layer, written only when the doc has embeddable
    # fonts. Toggled independently in the viewer; output.embedFonts sets whether
    # it starts enabled in the standalone HTML.
    embed_css = _embed_css(ir)
    if embed_css:
        (ctx.outdir / "embed.css").write_text(embed_css, encoding="utf-8")

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
    if embed_css:
        # starts enabled per config.output.embedFonts; the viewer flips
        # link.disabled live ("Use embedded fonts")
        off = "" if ctx.cfg["output"].get("embedFonts") else " disabled"
        links += (f'\n<link rel="stylesheet" href="embed.css" '
                  f'id="css-embed"{off}>')
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{links}
</head>
<body>
{_render_warnings(ir.get("warnings", []))}
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


def _render_warnings(warnings):
    """Doc-level advisory banner at the top of the page. Inline styles keep it
    visible regardless of which CSS layers are toggled, and self-contained in
    the exported HTML."""
    if not warnings:
        return ""
    rows = "\n".join(
        f'<p style="margin:.15em 0"><strong>{html.escape(w.get("title", ""))}</strong>'
        f' — {html.escape(w.get("detail", ""))}</p>'
        for w in warnings)
    return (
        '<aside class="rk-warnings" role="note" data-rk-warning="1" '
        'style="margin:0;padding:.7em 1.1em;background:#fff8e1;'
        'border-bottom:1px solid #e6c200;color:#5b4a00;font:14px/1.45 '
        '-apple-system,Segoe UI,Helvetica,Arial,sans-serif">'
        f'<span aria-hidden="true">⚠ </span>{rows}</aside>')


def _apply_ops(ctx, ir):
    """Edit ops: durable per-element operations (<name>.ops.json, written by
    the viewer). The user's one-off cleanups live here instead of as
    hyper-specific pipeline rules; they survive every re-render and cost no
    code. v1 vocabulary: set-text, delete, set-level."""
    ops = ctx.cfg.get("ops", [])
    if not ops:
        return
    by_nid = {}
    for op in ops:
        by_nid.setdefault(op.get("nid"), []).append(op)

    def transform(nodes):
        out = []
        for n in nodes:
            if n.get("children"):
                n["children"] = transform(n["children"])
            applied = by_nid.get(n.get("nid"), [])
            drop = False
            for op in applied:
                kind = op.get("op")
                if kind == "delete":
                    drop = True
                    ctx.log.entry("op-delete", nid=n["nid"],
                                  text=(n.get("text") or "")[:50])
                elif kind == "set-text" and "text" in n:
                    ctx.log.entry("op-set-text", nid=n["nid"],
                                  old=(n.get("text") or "")[:50],
                                  new=str(op.get("value", ""))[:50])
                    n["text"] = str(op.get("value", ""))
                    # replacement text invalidates char-range markup
                    for key in ("refs", "links", "breaks"):
                        n.pop(key, None)
                elif kind == "set-level":
                    level = int(op.get("value", 0))
                    ctx.log.entry("op-set-level", nid=n["nid"], level=level,
                                  was=f'{n["type"]}/{n.get("level")}')
                    if level <= 0 and n["type"] == "heading":
                        n["type"] = "paragraph"
                        n.pop("level", None)
                        n.pop("id", None)
                    elif level > 0:
                        if n["type"] == "paragraph":
                            n["type"] = "heading"
                            n["id"] = re.sub(r"[^a-z0-9]+", "-",
                                             (n.get("text") or "")[:60].lower()
                                             ).strip("-") or n["nid"]
                            for key in ("refs", "links", "breaks"):
                                n.pop(key, None)
                        if n["type"] == "heading":
                            n["level"] = min(level, 6)
                if drop:
                    break
            if not drop:
                out.append(n)
        return out

    ir["body"] = transform(ir["body"])


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


# provenance keys that the HTML/CSS actually consume; everything else in a
# node's `data` (font, weight, size, color, role, align…) is input to the
# generated stylesheet, NOT needed in the markup — keeping it out is most of
# what makes the HTML read as hand-authored rather than machine-dumped
_HTML_DATA_KEYS = {"marker"}


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
    # provenance stays in the review HTML (a future "output" view strips it);
    # it's useful when inspecting, and invisible to layout
    for k, v in (node.get("data") or {}).items():
        a[f"data-{k}"] = v
    if node.get("_cls"):
        a["class"] = node["_cls"]
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
    if t == "deflist":
        parts = []
        for c in node["children"]:
            if c.get("dl") == "dt":
                parts.append(f"  <dt {_attrs(c, pages)}>"
                             f"{html.escape(c['text'])}</dt>")
            else:
                body = _inline(c["text"], c.get("links"), c.get("refs"),
                               state, breaks=c.get("breaks"),
                               emph=c.get("emph"), marks=c.get("marks"))
                parts.append(f"  <dd {_attrs(c, pages)}>{body}</dd>")
        inner = "\n".join(parts)
        return f'<dl {_attrs(node, pages)}>\n{inner}\n</dl>'
    if t == "list":
        ordered = node.get("ordered")
        tag = "ol" if ordered else "ul"
        if (node.get("data") or {}).get("marker") == "»":
            # jump-marker lists: when the entries name in-document headings,
            # they are navigation, not content
            def jump_target(it):
                return (_resolve_anchor(it, state["anchors"])
                        or _resolve_anchor(
                            re.sub(r"(?i)^chapter\s+\d+:\s*", "", it),
                            state["anchors"]))

            resolved = [(_item_text(it), jump_target(_item_text(it)))
                        for it in node["items"]]
            hits = sum(1 for _it, tgt in resolved if tgt)
            if resolved and hits >= 0.6 * len(resolved):
                lis = "\n".join(
                    f'  <li><a href="#{tgt[0]}">{html.escape(it)}</a></li>'
                    if tgt else f"  <li>{html.escape(it)}</li>"
                    for it, tgt in resolved)
                return (f'<nav class="local-toc" aria-label="In this section" '
                        f'{_attrs(node, pages)}>\n<ul>\n{lis}\n</ul>\n</nav>')
        extra = {}
        if ordered in OL_TYPE:
            extra["type"] = OL_TYPE[ordered]
        if node.get("start", 1) and node.get("start", 1) > 1:
            extra["start"] = node["start"]
        parts = []
        for it in node["items"]:
            # items are rich dicts carrying style runs and/or a nested sub-list
            body = _item_inline(it, state)
            sub = it.get("sub") or {} if isinstance(it, dict) else {}
            if not sub:
                parts.append(f"  <li>{body}</li>")
                continue
            stype = f' type="{OL_TYPE[sub["ordered"]]}"' \
                if sub.get("ordered") in OL_TYPE else ""
            sstart = f' start="{sub["start"]}"' \
                if sub.get("start", 1) > 1 else ""
            subhtml = "\n".join(f"    <li>{_item_inline(s, state)}</li>"
                                for s in sub.get("items", []))
            parts.append(f"  <li>{body}\n"
                         f"  <ol{stype}{sstart}>\n{subhtml}\n  </ol></li>")
        items = "\n".join(parts)
        return f'<{tag} {_attrs(node, pages, extra or None)}>\n{items}\n</{tag}>'
    if t == "paragraph":
        lead = node.get("lead")
        emph = node.get("emph")
        marks = node.get("marks")
        if lead:
            # the lead's own styling comes from layer-3 .soft-header rules;
            # inline runs inside it would collide with the lead event
            emph = [r for r in (emph or []) if r[0] >= lead]
            marks = [r for r in (marks or []) if r[0] >= lead]
        body = _inline(node["text"], node.get("links"), node.get("refs"), state,
                       breaks=node.get("breaks"), emph=emph,
                       marks=marks, lead=lead)
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
        title = node.get("title")
        cap = node.get("caption")
        head = (f'  <figcaption>{html.escape(title)}</figcaption>\n'
                if title else "")
        if cap and title:
            # one figcaption per figure: the title heads it, the source/
            # caption line keeps its place below the image
            tail = f'\n  <p class="fig-source">{html.escape(cap)}</p>'
        elif cap:
            tail = f'\n  <figcaption>{html.escape(cap)}</figcaption>'
        else:
            tail = ""
        return (f'<figure {_attrs(node, pages)}>\n{head}'
                f'  <img src="{node["src"]}" alt="{html.escape(node["alt"], quote=True)}"'
                f' width="{node["width"]}">{tail}\n</figure>')
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
        if (node.get("data") or {}).get("duplicates"):
            # duplicated decoration: visible flourish, silent to screen
            # readers (floating pull-quotes are original text and stay heard)
            extra["aria-hidden"] = "true"
        return f'<aside {_attrs(node, pages, extra)}>\n{children}\n</aside>'
    if t == "columns":
        cells = {}
        for c in node["children"]:
            cells.setdefault(c.get("cell", 0), []).append(c)
        cols = []
        for ci in sorted(cells):
            inner = "\n".join(_render_node(ctx, c, pages, state)
                              for c in cells[ci])
            cols.append(f'<div class="col">\n{inner}\n</div>')
        joined = "\n".join(cols)
        return f'<div class="columns" {_attrs(node, pages)}>\n{joined}\n</div>'
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


def _item_text(it):
    """The plain text of a list item (rich dict, or a stray legacy string)."""
    return it if isinstance(it, str) else it.get("text", "")


def _item_inline(it, state):
    """Render a list item / sub-item, applying its style runs. Items are rich
    dicts (analyze guarantees it via _assert_rich_items); a bare string is
    tolerated defensively but carries no style by definition."""
    if isinstance(it, str):
        return html.escape(it)
    return _inline(it.get("text", ""), it.get("links"), None, state,
                   emph=it.get("emph"), marks=it.get("marks"))


# nesting order for overlapping wrap spans: lower rank = outer wrapper, so a
# bold+italic+linked title renders <a><strong><em>…. Fixed ranks make the
# segment sweep's nesting deterministic regardless of where spans start/end.
_WRAP_RANK = {"lead": 0, "link": 1, "mark": 2, "strong": 3, "em": 4}


def _inline(text, links, refs, state, breaks=None, emph=None, marks=None,
            lead=None):
    """Escape text and apply inline markup with NO silent drops on overlap.

    Two kinds of inline markup:
      - WRAP spans (link / strong / em / mark / lead) surround a range and may
        overlap arbitrarily. A segment sweep splits them at every boundary and
        nests them by `_WRAP_RANK`; spans that cross are closed and reopened so
        the output is always well-formed (e.g. link[10,20]+em[15,25] becomes
        <a>…<em>…</em></a><em>…</em>) — nothing is ever dropped.
      - REPLACEMENT events (br / footnote-sup / a url-as-text link) carve a
        fixed region whose markup is emitted verbatim; surrounding wrap spans
        stay open around them. Overlapping replacements are resolved by priority
        (a footnote ref outranks a link, which outranks a plain sup).
    `breaks` are offsets of join-spaces that render as <br>."""
    n = len(text)
    merged_links = []
    for s, e, target in sorted(links or []):
        if merged_links and s - merged_links[-1][1] <= 1 \
                and merged_links[-1][2] == target:
            merged_links[-1][1] = e  # one link wrapped across a line split
        else:
            merged_links.append([s, e, target])

    # --- wrap spans ------------------------------------------------------
    wraps = []  # (s, e, rank, open, close)
    if lead:
        wraps.append((0, lead, _WRAP_RANK["lead"],
                      '<b class="soft-header">', "</b>"))
    for s, e, color in (marks or []):
        # browsers default <mark> to yellow; non-yellow highlights carry their
        # color (provenance, not decoration - layer 2 keeps it)
        style = f' style="background: {color}"' \
            if color not in ("#ffff00", "#ffff66") else ""
        wraps.append((s, e, _WRAP_RANK["mark"], f"<mark{style}>", "</mark>"))
    for s, e, kind in (emph or []):
        if kind in ("strong", "em"):
            wraps.append((s, e, _WRAP_RANK[kind], f"<{kind}>", f"</{kind}>"))

    # --- replacement events ---------------------------------------------
    # collected as (s, e, prio, kind, data); markup is built AFTER overlap
    # resolution so footnote sequence numbers are only spent on survivors.
    raw_repls = [(s, s + 1, 3, "br", None) for s in (breaks or [])]
    for s, e, num in sorted(refs or []):
        prio = 0 if num in state["fn_nums"] else 2
        raw_repls.append((s, e, prio, "ref", num))

    link_events = [(s, e, t) for s, e, t in merged_links]
    if state.get("autolink"):
        occupied = ([(s, e) for s, e, _t in merged_links]
                    + [(s, e) for s, e, _n in (refs or [])]
                    + [(s, s + 1) for s in (breaks or [])]
                    + [(s, e) for s, e, _k in (emph or [])]
                    + [(s, e) for s, e, _c in (marks or [])])
        for s, e, _kind, payload in _autolink_events(text, occupied):
            link_events.append((s, e, payload))
    for s, e, payload in link_events:
        m = _link_markup(text, s, e, payload, state)
        if m[0] == "replace":
            raw_repls.append((s, e, 1, "linkrepl", m[1]))
        else:
            wraps.append((s, e, _WRAP_RANK["link"], m[1], m[2]))

    # resolve replacement overlaps: lowest prio number wins, earlier first
    raw_repls.sort(key=lambda r: (r[0], r[2]))
    chosen = []
    for r in raw_repls:
        if any(not (r[1] <= c[0] or r[0] >= c[1]) for c in chosen):
            continue
        chosen.append(r)
    repls = []  # (s, e, markup) built in text order
    for s, e, _prio, kind, data in sorted(chosen, key=lambda r: r[0]):
        if kind == "br":
            mk = "<br>\n"
        elif kind == "linkrepl":
            mk = data
        else:  # footnote / plain superscript reference
            seg = html.escape(text[s:e])
            if data in state["fn_nums"]:
                k = state["ref_seq"].get(data, 0) + 1
                state["ref_seq"][data] = k
                # spaces inside a marker are run-split artifacts ("i i" is ii)
                marker = seg.replace(" ", "")
                mk = (f'<sup class="fnref" id="fnref-{data}-{k}">'
                      f'<a href="#fn-{data}">{marker}</a></sup>')
            else:
                mk = f"<sup>{seg.replace(' ', '')}</sup>"
            if e < n and text[e].isalpha():
                mk += " "  # run splits often swallow the space after
        repls.append((s, e, mk))

    def _repl_cover(a, b):
        for rs, re_, mk in repls:
            if rs <= a and b <= re_:
                return rs, re_, mk
        return None

    # --- segment sweep ---------------------------------------------------
    pts = {0, n}
    for s, e, *_ in wraps:
        pts.add(s)
        pts.add(e)
    for s, e, _m in repls:
        pts.add(s)
        pts.add(e)
    pts = sorted(p for p in pts if 0 <= p <= n)

    out = []
    stack = []  # wrap tuples currently open, outer-first
    for a, b in zip(pts, pts[1:]):
        if a >= b:
            continue
        cover = _repl_cover(a, b)
        if cover:
            # inside a replacement: only wraps that surround the WHOLE region
            # stay open around it (a wrap poking partway in is ignored here)
            rs, re_, _mk = cover
            active = [w for w in wraps if w[0] <= rs and re_ <= w[1]]
        else:
            active = [w for w in wraps if w[0] <= a and b <= w[1]]
        active.sort(key=lambda w: (w[2], w[0], -w[1]))
        # close the stack down to its common prefix with `active`, then open
        # whatever `active` still needs (this is what splits crossing spans)
        cp = 0
        while cp < len(stack) and cp < len(active) and stack[cp] is active[cp]:
            cp += 1
        while len(stack) > cp:
            out.append(stack.pop()[4])
        for w in active[cp:]:
            out.append(w[3])
            stack.append(w)
        if cover:
            if a == cover[0]:
                out.append(cover[2])  # emit replacement markup once, at its start
        else:
            out.append(html.escape(text[a:b]))
    while stack:
        out.append(stack.pop()[4])
    return "".join(out)


def _link_markup(text, s, e, payload, state):
    """Markup for a link span: ('wrap', open, close) normally, or
    ('replace', markup) when the anchor text IS the url (print line-wraps
    corrupt it, so we emit the clean href as both text and target)."""
    uri = payload.get("uri")
    if payload.get("styled"):
        # print-styled cross-reference with no PDF target: if the text names a
        # heading/box in THIS document, link it; else a dead <a> would mislead
        target = _resolve_anchor(text[s:e], state["anchors"])
        if target:
            tid, tpage = target
            return ("wrap", f'<a href="#{tid}" data-link-styled="true" '
                    f'data-target-page="{tpage}">', "</a>")
        return ("wrap", '<span data-link-styled="true">', "</span>")
    if uri:
        href = uri if "://" in uri or uri.startswith(("mailto:", "#")) \
            else "https://" + uri
        cls = ' class="autolink"' if payload.get("auto") else ""
        raw = text[s:e]
        if raw.lstrip().lower().startswith(("http", "www.")) and \
                _alnum_only(raw) == _alnum_only(href):
            return ("replace", f'<a{cls} href="{html.escape(href, quote=True)}">'
                    f'{html.escape(href)}</a>')
        return ("wrap", f'<a{cls} href="{html.escape(href, quote=True)}">',
                "</a>")
    dest = payload.get("destPage")
    tid = state["pageTargets"].get(dest) \
        or next((state["pageTargets"][p]
                 for p in sorted(state["pageTargets"])
                 if p >= (dest or 0)), None)
    href = f' href="#{tid}"' if tid else ""
    return ("wrap", f'<a{href} data-dest-page="{dest}" '
            f'data-target-page="{dest}">', "</a>")


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

# families every platform ships (or ships a metric twin of) - pointless to
# fetch, and most aren't on Google Fonts anyway
SYSTEM_FAMILIES = {"helvetica", "arial", "times", "times new roman", "courier",
                   "courier new", "georgia", "verdana", "tahoma", "symbol",
                   "calibri", "cambria", "aptos", "segoe ui"}

MARKER_STYLE = {"•": "disc", "◦": "circle", "·": "disc", "»": '"» "',
                "◊": '"◊ "'}


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


def _dark(hex_color):
    """True for backgrounds dark enough to carry light text."""
    if not hex_color:
        return False
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b < 160


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


# nicer names for the common single-trait paragraph styles; multi-trait or
# unrecognised combinations fall back to a joined descriptive name
_STYLE_NICE = {
    ("lg",): "large", ("xl",): "display", ("sm",): "fine",
    ("lg", "strong"): "lead", ("xl", "strong"): "lead",
    ("sm", "italic"): "caption", ("italic",): "note",
    ("strong",): "strong-text", ("accent",): "accent",
    ("center",): "centered",
}


def _style_class_name(rules):
    """A readable, role-derived class for a paragraph style departure — replaces
    a pile of [data-nid="…"] selectors with one named class (e.g. .lead, .fine,
    .caption). Derived from the visual traits, never from coordinates/ids."""
    txt = " ".join(rules)
    traits = []
    m = re.search(r"font-size:\s*([\d.]+)em", txt)
    if m:
        sz = float(m.group(1))
        traits.append("xl" if sz >= 1.6 else "lg" if sz >= 1.12
                       else "sm" if sz <= 0.88 else "")
    if re.search(r"font-weight:\s*[6789]", txt):
        traits.append("strong")
    elif re.search(r"font-weight:\s*5", txt):
        traits.append("medium")
    if "font-style: italic" in txt:
        traits.append("italic")
    if "text-align: center" in txt:
        traits.append("center")
    elif "text-align: right" in txt:
        traits.append("right")
    if re.search(r"^\s*color:", txt, re.M):
        traits.append("accent")
    if re.search(r"font-family:[^;]*(?<!sans-)serif", txt):
        traits.append("serif")  # true serif only — 'sans-serif' must not match
    elif "font-family" in txt:
        traits.append("alt")
    traits = tuple(t for t in traits if t)
    return _STYLE_NICE.get(traits) or ("-".join(traits) if traits else "styled")


def _famkey(fam):
    """A CSS-identifier-safe key for a family name (used in the --rkf-* vars)."""
    return re.sub(r"[^a-z0-9]+", "", (fam or "").lower()) or "x"


def _embed_css(ir):
    """The @font-face layer (embed.css). Each element's font-family in
    original.css reads `var(--rkf-<family>, <fallback>)`; this layer is the ONLY
    place those vars are defined (pointing the family at its embedded face) and
    is where the @font-face rules live. So when the viewer disables this layer,
    the vars vanish and every rule's var() fallback drops cleanly to the guessed
    font — the element stops NAMING the embedded face entirely, which is robust
    against browsers that keep an already-loaded @font-face registered after its
    stylesheet is disabled. All cuts of a family share one family name at their
    true weight/style, so <strong>->Bold / <em>->Italic resolve naturally.
    Serving a licensed font is the user's responsibility (disclaimer below)."""
    embed = ir.get("fonts_embed") or {}
    if not embed:
        return ""
    out = ["/* Embedded fonts from the source PDF. If a font is licensed, it is",
           "   your responsibility to have the right to web-serve it. */", ""]
    fams, faces = {}, []
    for name in sorted(embed):
        fam, generic, weight, style = _font_css(name)
        fams[_famkey(fam)] = (fam, generic)
        faces += ['@font-face {',
                  f'  font-family: "PDFEmbed {fam}";',
                  f'  src: url("{embed[name]["file"]}") format("opentype");',
                  f'  font-weight: {weight or 400};',
                  f'  font-style: {style or "normal"};',
                  '}']
    # the toggle hinges on these var definitions, not on @font-face unloading
    out.append(":root {")
    for key, (fam, generic) in sorted(fams.items()):
        out.append(f'  --rkf-{key}: "PDFEmbed {fam}", "{fam}", {generic};')
    out.append("}")
    out += faces
    return "\n".join(out) + "\n"


def _original_css(ctx, ir):
    """Layer 3: best-effort recreation of the source document's look, built
    entirely from IR provenance. Regenerated on every render."""
    body, heads = _style_profile(ir)
    body_pt = body["size"] or 10.0
    out = ["/* Layer 3 — original-look styling, generated per document from",
           "   extraction provenance (fonts, colors, sizes). Do not edit:",
           "   regenerated by the render stage. */", ""]

    families = {}  # family -> {"weights", "italic"}: fetched from Google Fonts

    # "use the PDF's fonts": when output.embedFonts is on, the actual embedded
    # font programs were wrapped into OTFs by extract (manifest in ir). We serve
    # them via @font-face and name them as the PRIMARY family, so the rendering
    # is faithful and immune to a guessed/locally-installed same-named font (the
    # points-of-light failure). A program that couldn't be wrapped just isn't in
    # the manifest and falls back to the guessed family below.
    # always reference the embedded families (with fallback) when the doc has
    # them; the @font-face rules live in a separate embed.css layer the viewer
    # can toggle, so turning embedded fonts off just drops to the fallback.
    embed = ir.get("fonts_embed") or {}

    def fam_value(name, fam, generic):
        """font-family value. For an embedded font, route through a CSS var that
        ONLY embed.css defines (as "PDFEmbed <family>", "<family>", generic) — so
        with the embed layer off the var() fallback here drops cleanly to the
        guessed font and the element never names the embedded face. All cuts of a
        family share one "PDFEmbed <family>" name so <strong>/<em> pick the
        bold/italic face by weight/style — emphasis works like a real font."""
        if name in embed:
            return f'var(--rkf-{_famkey(fam)}, "{fam}", {generic})'
        return f'"{fam}", {generic}'

    def note_family(name, fam, weight, style):
        low = (fam or "").lower()
        if not fam or name in embed or low in SYSTEM_FAMILIES \
                or low.split()[0] in SYSTEM_FAMILIES:
            return  # embedded families are served locally, never fetched
        f = families.setdefault(fam, {"weights": set(), "italic": False})
        f["weights"].add(weight or 400)
        if style == "italic":
            f["italic"] = True

    body_fam = None
    if body["font"] or body["color"]:
        fam, generic, weight, style = _font_css(body["font"] or "")
        body_fam = fam or None
        rules = []
        if fam:
            rules.append(f'  font-family: {fam_value(body["font"], fam, generic)};')
            # ALWAYS pin the body weight. Without it the body inherits the
            # browser default (or, worse, whatever cut a stray local install of
            # a same-named font ships) — that's how points-of-light rendered
            # near-bold: bare "Gotham" matched a heavy local face. An explicit
            # weight asks for the right cut (and embedFonts removes the ambiguity
            # entirely by serving the actual program).
            rules.append(f"  font-weight: {weight or 400};")
            if style:
                rules.append(f"  font-style: {style};")
            note_family(body["font"], fam, weight, style)
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
            rules.append(f'  font-family: {fam_value(h["font"], fam, generic)};')
            note_family(h["font"], fam, weight, style)
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

    # links: original documents color their links and (almost always) skip
    # the underline; learn the color from link-dominated paragraphs
    link_votes = Counter()

    def feed_links(n):
        if n["type"] != "paragraph":
            return  # headings with links carry heading color, not link color
        links = n.get("links") or []
        own = _usable_color((n.get("data") or {}).get("color"))
        if own:
            r, g, b = (int(own[i:i + 2], 16) for i in (1, 3, 5))
            if max(r, g, b) - min(r, g, b) < 24:
                own = None  # greys aren't link styling, just dark text
        if links and own and own != body["color"]:
            span = sum(e - s for s, e, _ in links)
            if span >= 0.6 * max(len(n.get("text", "") or ""), 1):
                link_votes[own] += span

    # paragraph style exceptions: font/color/size/alignment departures from
    # the body profile; identical departures share one grouped rule
    groups = {}
    group_order = []
    link_exceptions = {}  # color -> [nid]: link paragraphs off the a-rule
    lead_groups = {}      # rules tuple -> [nid]: soft-header lead styling

    def feed_exception(n):
        if n["type"] != "paragraph" and n.get("dl") != "dt":
            return
        d = n.get("data") or {}
        rules = []
        if d.get("font") and d["font"] != (body["font"] or ""):
            fam, generic, weight, style = _font_css(d["font"])
            _, _, b_weight, b_style = _font_css(body["font"] or "")
            if fam:
                note_family(d["font"], fam, weight, style)
                if fam != body_fam or d["font"] in embed:
                    rules.append(f'  font-family: {fam_value(d["font"], fam, generic)};')
                if weight and weight != b_weight:
                    rules.append(f"  font-weight: {weight};")
                if style and style != b_style:
                    rules.append(f"  font-style: {style};")
        own = _usable_color(d.get("color"))
        # a link-dominated paragraph's color IS the link color: the `a`
        # rule styles it, the surrounding text keeps body color (documents
        # that mix link colors get per-node a-rules below)
        link_span = sum(e - s for s, e, _t in n.get("links") or [])
        link_dom = link_span >= 0.5 * max(len(n.get("text", "") or ""), 1)
        if own and own != body["color"]:
            if link_dom:
                link_exceptions.setdefault(own, []).append(n["nid"])
            else:
                rules.append(f"  color: {own};")
        if d.get("size") and abs(d["size"] / body_pt - 1) >= 0.12:
            rules.append(f"  font-size: {round(d['size'] / body_pt, 2)}em;")
        if d.get("align"):
            rules.append(f"  text-align: {d['align']};")
        if d.get("indentKeep") and d.get("indent"):
            rules.append(f"  margin-left: {d['indent']}em;")
        if rules:
            key = tuple(rules)
            if key not in groups:
                group_order.append(key)
            groups.setdefault(key, []).append(n)
        if d.get("leadFont") or d.get("leadColor"):
            lrules = []
            if d.get("leadFont"):
                fam, generic, weight, style = _font_css(d["leadFont"])
                if fam and (fam != body_fam or d["leadFont"] in embed):
                    lrules.append(f'  font-family: {fam_value(d["leadFont"], fam, generic)};')
                    note_family(d["leadFont"], fam, weight, style)
                if weight:
                    lrules.append(f"  font-weight: {weight};")
                if style:
                    lrules.append(f"  font-style: {style};")
            lc = _usable_color(d.get("leadColor"))
            if lc and lc != body["color"]:
                lrules.append(f"  color: {lc};")
            if lrules:
                lead_groups.setdefault(tuple(lrules), []).append(n["nid"])

    def feed_all(nodes):
        for n in nodes:
            feed_links(n)
            feed_exception(n)
            feed_all(n.get("children", []))

    feed_all(ir["body"])

    if link_votes:
        link_color = link_votes.most_common(1)[0][0]
        out += ["a {", f"  color: {link_color};",
                "  text-decoration: none;", "}",
                "a:hover { text-decoration: underline; }", ""]
        # documents that mix link colors: the minority styles keep theirs
        for c in sorted(link_exceptions):
            if c == link_color:
                continue
            sel = ",\n".join(f'[data-nid="{nid}"] a'
                             for nid in link_exceptions[c])
            out += [f"{sel} {{ color: {c}; }}", ""]

    # paragraph style departures become ONE named class each (.lead/.fine/…),
    # tagged onto the nodes, instead of a list of [data-nid] selectors
    used_names = {}
    for key in group_order:
        name = base = _style_class_name(key)
        i = 2
        while name in used_names and used_names[name] != key:
            name = f"{base}-{i}"
            i += 1
        used_names[name] = key
        for n in groups[key]:
            n["_cls"] = (n.get("_cls", "") + " " + name).strip()
        out += [f".{name} {{", *key, "}", ""]

    for key in sorted(lead_groups):
        sel = ",\n".join(f'[data-nid="{nid}"] .soft-header'
                         for nid in lead_groups[key])
        out += [f"{sel} {{", *key, "}", ""]

    # callout boxes keep their original fill/border and (when narrower than
    # the column) their floated position and width; floated figures too
    for n in ir["body"]:
        d = n.get("data") or {}
        if n["type"] == "heading":
            # heading whose own color differs from its level's dominant color
            lv_color = heads.get(n["level"], {}).get("color")
            own = _usable_color(d.get("color"))
            if own and lv_color and own != lv_color:
                out += [f'[data-nid="{n["nid"]}"] {{ color: {own}; }}', ""]
        if n["type"] == "table" and n.get("style"):
            st = n["style"]
            sel = f'[data-nid="{n["nid"]}"]'
            if st.get("border"):
                out += [f"{sel} th, {sel} td {{ "
                        f"border-color: {st['border']}; }}"]
            if st.get("headBg"):
                props = [f"background: {st['headBg']};"]
                fg = st.get("headFg")
                if fg and (_usable_color(fg) or _dark(st["headBg"])):
                    props.append(f"color: {fg};")
                out += [f"{sel} thead th {{ {' '.join(props)} }}"]
            n_cols = max(len(st.get("colBg") or []),
                         len(st.get("colFg") or []))
            for ci in range(n_cols):
                props = []
                bg = (st.get("colBg") or [None] * n_cols)[ci]
                fg = (st.get("colFg") or [None] * n_cols)[ci]
                if bg and bg != "#ffffff":
                    props.append(f"background: {bg};")
                if fg and fg != body["color"] \
                        and (_usable_color(fg) or _dark(bg)):
                    props.append(f"color: {fg};")
                if props:
                    out += [f"{sel} td:nth-child({ci + 1}) "
                            f"{{ {' '.join(props)} }}"]
            out += [""]
        rules = []
        if n["type"] == "aside":
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
            out += [f'[data-nid="{n["nid"]}"] {{', *rules, "}", ""]

    # the original has no figure chrome; layer 2's box is greyscale dressing
    out += ["figure { border: none; padding: 0; }", ""]

    # fetch non-system families from Google Fonts (≈80% of documents use one).
    # Two imports per family: a bare one that succeeds for any family Google
    # has, and an exact-weights one that upgrades it when those cuts exist -
    # a 400 on either is harmless, the rest of the sheet still applies.
    imports = []
    for fam in sorted(families):
        f = families[fam]
        q = fam.replace(" ", "+")
        base = f"https://fonts.googleapis.com/css2?family={q}"
        imports.append(f'@import url("{base}&display=swap");')
        wlist = sorted(f["weights"] | {400})
        if f["italic"]:
            tuples = (";".join(f"0,{w}" for w in wlist) + ";"
                      + ";".join(f"1,{w}" for w in wlist))
            axis = f":ital,wght@{tuples}"
        else:
            axis = ":wght@" + ";".join(str(w) for w in wlist)
        if axis != ":wght@400":
            imports.append(f'@import url("{base}{axis}&display=swap");')
    if imports:
        out[4:4] = imports + [""]

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
