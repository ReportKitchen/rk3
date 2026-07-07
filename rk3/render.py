"""Render stage: IR -> semantic HTML + 3 CSS layers + reconstructed nav.

Engine-agnostic: consumes ir.json only. Every element carries data-rk (debug
log key) and data-page (source page) plus any other provenance under data-*.
"""

import html
import json
import re
import shutil
from collections import Counter
from pathlib import Path

from . import irwalk

VERSION = 84

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
    # footnote anchors: unique even when numbering RESTARTS per page (toolkit's
    # 1,2,3 on every page); in-text refs only become anchors when the note
    # exists, and resolve to the same-page (or nearest) instance of their number
    fn_keys, fn_by_n = _fn_keys(ir)
    state = {"fn_nums": set(fn_by_n),
             "fn_keys": fn_keys,
             "fn_by_n": fn_by_n,
             "ref_seq": {},
             "autolink": ctx.cfg["output"].get("autolinkUrls", True),
             "anchors": _anchor_targets(ir),
             "pageTargets": _page_targets(ir)}
    # QA flags are document-level annotations, not content: pull them out of the
    # body so a saved reading-order reorder op (whose nid list can't include a
    # freshly-minted flag) never sorts them to the bottom. They render pinned at
    # the very top, before the outline.
    flag_nodes = [n for n in ir["body"] if n.get("type") == "flag"]
    parts = [_render_node(ctx, node, pages, state)
             for node in ir["body"] if node.get("type") != "flag"]
    flags_html = "\n".join(_render_node(ctx, n, pages, state) for n in flag_nodes)

    nav = _render_nav(ir)
    title = html.escape(ir.get("title", "Document"))
    layers = ctx.cfg["output"].get("cssLayers", ["layout", "default", "original"])
    links = "\n".join(
        f'<link rel="stylesheet" href="{layer}.css" id="css-{layer}">'
        for layer in ("layout", "default", "original") if layer in layers)
    if embed_css:
        # default state: "auto" embeds only when every font is fully covered
        # (ir.fonts_complete); a per-doc config can force true/false. The viewer
        # flips link.disabled live and persists the user's choice to the config.
        mode = ctx.cfg["output"].get("embedFonts", "auto")
        embed_on = bool(ir.get("fonts_complete", True)) if mode == "auto" \
            else bool(mode)
        off = "" if embed_on else " disabled"
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
{flags_html}
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

    # design-token digest (webified §5.6): the palette/scale the doc uses, for
    # inspection and as the styleTokens (§3.5) substrate. A derived local artifact
    # like scoreboard.json — regenerated each convert, not a committed baseline.
    (ctx.outdir / "styleguide.json").write_text(
        json.dumps(_styleguide(ir), indent=2, ensure_ascii=False),
        encoding="utf-8")
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
    code. v1 vocabulary: set-text, delete, set-level, note.

    `note` is the manual footnote-rescue op (for docs whose markers are too
    entangled with charts to auto-detect, e.g. gates-earth): the user tags a
    stranded note element `#note N`; we lift its text into a fielded note
    record, drop the element from the flow, fold it into the end data copy, and
    refresh the reconciliation flag."""
    ops = ctx.cfg.get("ops", [])
    if not ops:
        return
    by_nid = {}
    for op in ops:
        by_nid.setdefault(op.get("nid"), []).append(op)
    collected = []
    ref_applied = [False]
    # ref ops are idempotent: a `#ref N` only adds a reference when N isn't
    # already detected anywhere (so a mark that auto-detection later recovers
    # can't double-add a superscript).
    existing_ref_vals = set()

    for u in irwalk.walk(ir["body"]):
        for r in (u.get("refs") or []):
            existing_ref_vals.add(r[2])

    def transform(nodes):
        out = []
        for n in nodes:
            if n.get("children"):
                n["children"] = transform(n["children"])
            applied = by_nid.get(n.get("nid"), [])
            drop = False
            for op in applied:
                kind = op.get("op")
                if kind == "note" and "text" in n:
                    val = _note_op_value(op.get("n"))
                    if val is not None:
                        rec = {"n": val, "marker": str(op.get("n")),
                               "page": op.get("page", n.get("page")),
                               "text": n["text"], "rk": n.get("rk", "op-note")}
                        for k in ("links", "emph", "marks", "colors"):
                            if n.get(k):
                                rec[k] = n[k]
                        collected.append(rec)
                        drop = True
                        ctx.log.entry("op-note", nid=n["nid"], n=op.get("n"),
                                      text=(n.get("text") or "")[:50])
                elif kind == "ref" and "text" in n:
                    # manual reference rescue: the tagged element cites note N
                    # but the superscript was detached/dropped. Add it (as an
                    # end-of-text superscript link) unless N is already detected.
                    val = _note_op_value(op.get("n"))
                    if val is not None and val not in existing_ref_vals:
                        raw = str(op.get("n"))
                        s = len(n["text"])
                        n["text"] = n["text"] + raw
                        n.setdefault("refs", []).append([s, s + len(raw), val])
                        existing_ref_vals.add(val)
                        ref_applied[0] = True
                        ctx.log.entry("op-ref", nid=n["nid"], n=op.get("n"))
                elif kind == "delete":
                    drop = True
                    ctx.log.entry("op-delete", nid=n["nid"],
                                  text=(n.get("text") or "")[:50])
                elif kind == "set-text" and "text" in n:
                    ctx.log.entry("op-set-text", nid=n["nid"],
                                  old=(n.get("text") or "")[:50],
                                  new=str(op.get("value", ""))[:50])
                    n["text"] = str(op.get("value", ""))
                    n["_op"] = "set-text"
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

    if collected:
        # fold the rescued notes into the end data copy (create it if the doc
        # had no collected notes at all), deduped by (page, n), then refresh the
        # reconciliation flag so the "missing footnotes" count drops accordingly.
        data = next((n for n in ir["body"] if n.get("type") == "footnotes"
                     and n.get("variant") == "data"), None)
        if data is None:
            data = {"type": "footnotes", "variant": "data", "notes": [],
                    "page": collected[-1]["page"], "bbox": [0, 0, 0, 0],
                    "data": {}, "nid": "n-fn-data-ops"}
            ir["body"].append(data)
        have = {(nt.get("page"), nt["n"]) for nt in data["notes"]}
        for c in collected:
            if (c["page"], c["n"]) not in have:
                data["notes"].append(c)
                have.add((c["page"], c["n"]))
        data["notes"].sort(key=lambda x: (x.get("page") or 0, x["n"]))
        ctx.log.entry("op-note-collect", count=len(collected),
                      total=len(data["notes"]))

    if collected or ref_applied[0]:
        _refresh_flag(ir)

    # reorder ops from the viewer's reading-order tool. A doc-level op (no page)
    # lists ALL top-level nids in the corrected reading order — reorder the whole
    # body to match (nodes not listed keep their relative order at the end). A
    # page-scoped op permutes just that page's contiguous run of nodes.
    doc_order = next((op["order"] for op in reversed(ops)  # last save wins
                      if op.get("op") == "reorder" and op.get("order")
                      and op.get("page") is None), None)
    if doc_order:
        rank = {nid: i for i, nid in enumerate(doc_order)}

        def _reorder(nodes):
            # sort each level by the saved reading-order rank. A node NOT in
            # the saved order (created since the op was saved, or one the
            # editor skipped — tenure's un-mergeable figure) must NOT sink to
            # the document end: it interpolates after the listed node that
            # precedes it in the ENGINE's order (the struct-tree
            # interpolation move), so it stays where the engine put it.
            keys, last, frac = {}, -1, 0
            moved = {}
            prev_nid = None
            for n in nodes:
                nid = n.get("nid")
                r = rank.get(nid)
                if r is not None:
                    keys[id(n)] = (r, 0)
                    last, frac = r, 0
                else:
                    frac += 1
                    keys[id(n)] = (last, frac)
                moved[id(n)] = prev_nid   # engine-order predecessor
                prev_nid = nid
            nodes.sort(key=lambda n: keys[id(n)])
            # QA marking: a node whose predecessor changed was MOVED by the
            # op — render outlines it (the user's review trail)
            prev_nid = None
            for n in nodes:
                if moved[id(n)] != prev_nid and not n.get("_op"):
                    n["_op"] = "reorder"
                prev_nid = n.get("nid")
                if n.get("children"):
                    _reorder(n["children"])

        _reorder(ir["body"])
        ctx.log.entry("op-reorder-doc", count=len(doc_order))
    page_reorders = {op["page"]: op["order"] for op in ops
                     if op.get("op") == "reorder" and op.get("order")
                     and op.get("page") is not None}
    for page, seq in page_reorders.items():
        rank = {nid: i for i, nid in enumerate(seq)}
        slots = [k for k, n in enumerate(ir["body"]) if n.get("page") == page]
        nodes = sorted((ir["body"][k] for k in slots),
                       key=lambda n: rank.get(n["nid"], len(rank)))
        for slot, node in zip(slots, nodes):
            ir["body"][slot] = node
        ctx.log.entry("op-reorder", page=page, count=len(slots))

    # merge ops: fold node `frm` into node `into` (a paragraph the user rejoined
    # in the reading-order tool — usually a sentence split across a column break).
    # Run after reorder so the corrected adjacency is in place.
    for op in ops:
        if op.get("op") != "merge" or not (op.get("into") and op.get("frm")):
            continue
        a = _find_node(ir["body"], op["into"])
        holder, b = _find_node_parent(ir["body"], op["frm"])
        if a is None or b is None or a is b or "text" not in a or "text" not in b:
            # a skipped op must be LOUD (surface-failures): the user watched
            # a figure-merge do nothing and reasonably concluded the tool was
            # broken. Log the reason; the viewer can surface it later.
            reason = ("into not found" if a is None else
                      "frm not found" if b is None else
                      "same node" if a is b else
                      "into is not a text node" if "text" not in a else
                      "frm is not a text node (merge only joins text; use "
                      "reorder to move a figure)")
            ctx.log.entry("op-merge-skipped", into=op["into"], frm=op["frm"],
                          reason=reason)
            continue
        _merge_into(a, b)
        holder.remove(b)
        a["_op"] = "merge"
        ctx.log.entry("op-merge", into=op["into"], frm=op["frm"])


_find_node = irwalk.find
_find_node_parent = irwalk.find_parent


def _merge_into(a, b):
    """Concatenate b's text + style runs onto a (rebased), dropping nothing —
    the split-paragraph rejoin (cf. analyze._join_broken_paragraphs) as an op."""
    sep = " " if a.get("text") and not a["text"].endswith(("-", " ")) else ""
    off = len(a.get("text", "")) + len(sep)
    a["text"] = a.get("text", "") + sep + b.get("text", "")
    for key in ("emph", "links", "marks", "sups", "refs", "colors"):
        if b.get(key):
            a[key] = a.get(key, []) + [[s + off, e + off, *rest]
                                       for s, e, *rest in b[key]]
    if b.get("breaks"):
        a["breaks"] = a.get("breaks", []) + [x + off for x in b["breaks"]]


def _fn_display_r(val):
    """Human label for a note index (letters live at 1000+)."""
    return chr(val - 1000 + 96) if val > 1000 else str(val)


def _note_op_value(raw):
    """A `note` op's index -> internal value: arabic int, single letter at
    1000+ ('a'=1001, matching analyze), else None."""
    if raw is None:
        return None
    s = str(raw).strip()
    if s.isdigit():
        return int(s)
    if len(s) == 1 and s.isalpha():
        return 1000 + ord(s.lower()) - 96
    return None


def _reconcile_lists(ir):
    """Recompute (refs-without-note, notes-without-ref) as display strings,
    counting notes across every footnotes node (deduped). Used to refresh the
    flag after manual note-collection ops change the collected set."""
    ref_vals, note_vals = set(), set()

    for u in irwalk.walk(ir["body"]):
        for r in (u.get("refs") or []):
            ref_vals.add(r[2])
        if u.get("type") == "footnotes":
            for nt in u["notes"]:
                note_vals.add(nt["n"])
    rn = [_fn_display_r(v) for v in sorted(v for v in ref_vals if v not in note_vals)]
    nr = [_fn_display_r(v) for v in sorted(v for v in note_vals if v not in ref_vals)]
    return rn, nr


def _refresh_flag(ir):
    """Rebuild the footnote-mismatch flag node in place (or remove it once the
    doc fully reconciles)."""
    rn, nr = _reconcile_lists(ir)
    flag = next((n for n in ir["body"] if n.get("type") == "flag"), None)
    if not rn and not nr:
        if flag:
            ir["body"].remove(flag)
        return
    if flag:
        flag["refs_no_note"], flag["notes_no_ref"] = rn, nr
    else:
        ir["body"].insert(0, {"type": "flag", "kind": "footnote-mismatch",
                              "refs_no_note": rn, "notes_no_ref": nr,
                              "page": 1, "bbox": [0, 0, 0, 0], "data": {},
                              "nid": "n-flag-fn"})


def _fmt_flag_vals(vals):
    """Compress a list of index display strings into runs: [1,4,8,9,10,11,12,'a']
    -> '1, 4, 8–12, a'. Keeps non-numeric labels (letters) at the end."""
    ints = sorted({int(v) for v in vals if str(v).isdigit()})
    others = [str(v) for v in vals if not str(v).isdigit()]
    parts, i = [], 0
    while i < len(ints):
        j = i
        while j + 1 < len(ints) and ints[j + 1] == ints[j] + 1:
            j += 1
        parts.append(f"{ints[i]}–{ints[j]}" if j > i else str(ints[i]))
        i = j + 1
    return ", ".join(parts + others)


def _fn_keys(ir):
    """Anchor keys for every footnote: plain "n" while the number is unique
    doc-wide, "page-n" when numbering restarts per page. Returns
    ({(page, n): key}, {n: [(page, key), …]}).

    The notes appear TWICE in the body (in-place copy + end data copy), so
    dedupe by (page, n) — otherwise every doc-unique number looks duplicated
    and wrongly switches to per-page keying."""
    per_n = {}
    seen = set()
    for node in ir["body"]:
        if node["type"] == "footnotes":
            for note in node["notes"]:
                pn = (note.get("page"), note["n"])
                if pn in seen:
                    continue
                seen.add(pn)
                per_n.setdefault(note["n"], []).append(note)
    keys, by_n = {}, {}
    for n, notes in per_n.items():
        for note in notes:
            key = str(n) if len(notes) == 1 else f"{note.get('page')}-{n}"
            keys[(note.get("page"), n)] = key
            by_n.setdefault(n, []).append((note.get("page"), key))
    return keys, by_n


def _resolve_fn(state, num, page):
    """The anchor key for reference `num` seen on `page`: same-page note wins,
    else the nearest instance (a bottom-of-page footnote lives on the page
    that cites it; doc-wide numbering has exactly one candidate)."""
    cands = state["fn_by_n"].get(num) or []
    if not cands:
        return None
    if len(cands) == 1 or page is None:
        return cands[0][1]
    return min(cands, key=lambda pk: abs((pk[0] or 0) - page))[1]


def _norm_anchor(text):
    return irwalk.norm_key(text)


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
    if node.get("_op"):
        # QA trail: this element was touched by a saved edit op (moved by a
        # reorder, merge target, replaced text). CSS outlines it so the user
        # can see WHERE their hand-corrections are standing in for the engine
        a["data-op"] = node["_op"]
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
    if t == "flag":
        # QA banner at the top of the document (no flags panel yet). Currently
        # only footnote ref<->note mismatches; the shape generalizes. Values are
        # range-compressed ("1, 4, 8–12, 112–426") with a count so a badly
        # under-collected doc reads as a summary, not a wall of numbers.
        rows = []
        if node.get("refs_no_note"):
            vals = node["refs_no_note"]
            rows.append(f"<li>References with no matching note ({len(vals)}): "
                        f'<strong>{html.escape(_fmt_flag_vals(vals))}</strong></li>')
        if node.get("notes_no_ref"):
            vals = node["notes_no_ref"]
            rows.append(f"<li>Notes with no matching reference ({len(vals)}): "
                        f'<strong>{html.escape(_fmt_flag_vals(vals))}</strong></li>')
        return (f'<div class="rk-flags" {_attrs(node, pages)}>\n'
                '  <p class="rk-flags-title">⚑ Footnote mismatch</p>\n'
                f'  <ul>\n    ' + "\n    ".join(rows) + '\n  </ul>\n</div>')
    if t == "heading":
        lv = min(max(node["level"], 1), 6)
        # a heading is text too: run it through _inline so a footnote reference
        # in a title renders as a linked superscript, not a bare digit
        body = _inline(node["text"], node.get("links"), node.get("refs"), state,
                       emph=node.get("emph"), marks=node.get("marks"),
                       colors=node.get("colors"), page=node.get("page"))
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
                               emph=c.get("emph"), marks=c.get("marks"),
                               colors=c.get("colors"), page=c.get("page"))
                parts.append(f"  <dd {_attrs(c, pages)}>{body}</dd>")
        inner = "\n".join(parts)
        return f'<dl {_attrs(node, pages)}>\n{inner}\n</dl>'
    if t == "list":
        ordered = node.get("ordered")
        tag = "ol" if ordered else "ul"
        entries = node.get("children", [])

        def lead_text(it):
            # an item's first text leaf carries the item's text
            return next((ch.get("text", "") for ch in it.get("children", [])
                         if ch.get("text")), "")

        if (node.get("data") or {}).get("marker") == "»":
            # jump-marker lists: when the entries name in-document headings,
            # they are navigation, not content
            def jump_target(it):
                return (_resolve_anchor(it, state["anchors"])
                        or _resolve_anchor(
                            re.sub(r"(?i)^chapter\s+\d+:\s*", "", it),
                            state["anchors"]))

            resolved = [(lead_text(it), jump_target(lead_text(it)))
                        for it in entries]
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
        for it in entries:
            # an item is a container — its lead text leaf renders inline in
            # the <li>, everything else (nested list, and any node type
            # tomorrow) renders as itself
            inner = ""
            for ch in it.get("children", []):
                if ch.get("type") == "paragraph" and not inner:
                    inner = _inline(ch.get("text", ""), ch.get("links"),
                                    ch.get("refs"), state,
                                    breaks=ch.get("breaks"),
                                    emph=ch.get("emph"), marks=ch.get("marks"),
                                    colors=ch.get("colors"),
                                    page=ch.get("page"))
                else:
                    inner += "\n  " + _render_node(ctx, ch, pages, state)
            parts.append(f'  <li data-nid="{it["nid"]}">{inner}</li>')
        items = "\n".join(parts)
        return f'<{tag} {_attrs(node, pages, extra or None)}>\n{items}\n</{tag}>'
    if t == "paragraph":
        lead = node.get("lead")
        emph = node.get("emph")
        marks = node.get("marks")
        colors = node.get("colors")
        if lead:
            # the lead's own styling comes from layer-3 .soft-header rules;
            # inline runs inside it would collide with the lead event
            emph = [r for r in (emph or []) if r[0] >= lead]
            marks = [r for r in (marks or []) if r[0] >= lead]
            colors = [r for r in (colors or []) if r[0] >= lead]
        body = _inline(node["text"], node.get("links"), node.get("refs"), state,
                       breaks=node.get("breaks"), emph=emph,
                       marks=marks, lead=lead, colors=colors,
                       page=node.get("page"))
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
        # unified shape: title/caption are caption containers whose lead text
        # leaf renders inline (refs/links in captions work like anywhere else);
        # legacy string title/caption shimmed until step 5
        def cap_inline(c):
            leaf = next((ch for ch in c.get("children", [])
                         if ch.get("text")), None)
            if leaf is None:
                return ""
            return _inline(leaf.get("text", ""), leaf.get("links"),
                           leaf.get("refs"), state, breaks=leaf.get("breaks"),
                           emph=leaf.get("emph"), marks=leaf.get("marks"),
                           colors=leaf.get("colors"), page=leaf.get("page"))

        caps = [c for c in node.get("children", [])
                if c.get("type") == "caption"]
        tnode = next((c for c in caps if c.get("variant") == "title"), None)
        cnode = next((c for c in caps if c.get("variant") == "caption"), None)

        def _capsattr(cn):
            # caps mirroring (webified §5.1): the caption's inner leaf carries
            # data.caps when the source kicker renders ALL-CAPS from lowercase
            # codepoints (the figcaption is built by hand, not via _attrs)
            leaf = next((c for c in cn.get("children", []) if c.get("text")), None)
            return ' data-caps="1"' if leaf and (leaf.get("data") or {}).get("caps") else ""

        head = (f'  <figcaption data-nid="{tnode["nid"]}"{_capsattr(tnode)}>'
                f'{cap_inline(tnode)}</figcaption>\n') if tnode is not None \
            else ""
        if cnode is not None:
            body = cap_inline(cnode)
            # one figcaption per figure: a title heads it, the source/caption
            # line keeps its place below the image
            tail = (f'\n  <p class="fig-source" data-nid="{cnode["nid"]}"{_capsattr(cnode)}>'
                    f'{body}</p>' if head else
                    f'\n  <figcaption data-nid="{cnode["nid"]}"{_capsattr(cnode)}>'
                    f'{body}</figcaption>')
        else:
            tail = ""
        # placement evidence from analyze (figures plan phase 5): narrow
        # side-hugging figures float, content-width figures span
        flo = (node.get("data") or {}).get("float")
        fig_cls = {"left": ' class="fig-float-left"',
                   "right": ' class="fig-float-right"',
                   "wide": ' class="fig-wide"'}.get(flo, "")
        return (f'<figure{fig_cls} {_attrs(node, pages)}>\n{head}'
                f'  <img src="{node["src"]}" alt="{html.escape(node["alt"], quote=True)}"'
                f' width="{node["width"]}">{tail}\n</figure>')
    if t == "table":
        # unified container model: table > row > cell > leaf children. A cell
        # renders whatever nodes it holds (today a paragraph leaf; tomorrow a
        # figure or a list) — no cell-specific text handling. Rows/cells carry
        # only data-nid (addressable by ops/feedback); page/rk provenance lives
        # on the enclosing figure.
        # a table region's bound title/caption ride as caption containers
        # among the children (baystate p12); rows are selected by type
        rows = [c for c in node["children"] if c.get("type") == "row"]
        caps = [c for c in node["children"] if c.get("type") == "caption"]

        def _cell(c, tag):
            inner = "".join(_render_node(ctx, ch, pages, state)
                            for ch in c.get("children", []))
            return f'<{tag} data-nid="{c["nid"]}">{inner}</{tag}>'

        def _figcap(c):
            inner = "".join(_render_node(ctx, ch, pages, state)
                            for ch in c.get("children", []))
            return (f'<figcaption class="{c.get("variant", "caption")}" '
                    f'data-nid="{c["nid"]}">{inner}</figcaption>\n')

        head = ""
        body_rows = rows
        if node.get("header") and len(rows) > 1:
            head = ("<thead><tr>"
                    + "".join(_cell(c, "th") for c in rows[0]["children"])
                    + "</tr></thead>\n")
            body_rows = rows[1:]
        body = "\n".join(
            f'  <tr data-nid="{r["nid"]}">'
            + "".join(_cell(c, "td") for c in r["children"]) + "</tr>"
            for r in body_rows)
        title_caps = "".join(_figcap(c) for c in caps
                             if c.get("variant") == "title")
        tail_caps = "".join(_figcap(c) for c in caps
                            if c.get("variant") != "title")
        return (f'<figure class="table" {_attrs(node, pages)}>\n{title_caps}'
                f'<table>\n{head}<tbody>\n{body}\n</tbody>\n</table>\n'
                f'{tail_caps}</figure>')
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
        is_data = node.get("variant") == "data"
        items = []
        for note in node["notes"]:
            n = note["n"]
            key = state["fn_keys"].get((note.get("page"), n), str(n))
            # alphabetic designators (a, b, c — table notes) live at 1000+.
            # Display THE MARKER THE SOURCE USED: per-item lower-alpha style +
            # un-namespaced value renders "f." — never a bare number colliding
            # with the numbered references sharing the list (cleanair mixes
            # lettered page-notes with numbered endnotes)
            display = n - 1000 if n > 1000 else n
            li_style = ' style="list-style-type: lower-alpha"' if n > 1000 else ""
            if is_data:
                # data copy: plain <li>, no back-link chrome, but carry the
                # ref<->note wiring so tooltip JS (future) can find both ends
                refids = " ".join(f"fnref-{key}-{k}"
                                  for k in range(1, state["ref_seq"].get(key, 0) + 1))
                attrs = (f'value="{display}"{li_style} data-fn-key="{key}" '
                         f'data-fn-index="{html.escape(_fn_display_r(n))}"'
                         + (f' data-ref-ids="{refids}"' if refids else ""))
                # op-rescued notes carry the source element's inline runs; keep
                # bold/ital/links (analyze-collected notes have none -> plain)
                body = _inline(note["text"], note.get("links"), None, state,
                               emph=note.get("emph"), marks=note.get("marks"),
                               colors=note.get("colors"))
                items.append(f'  <li {attrs}>{body}</li>')
                continue
            back = (f' <a class="fn-back" href="#fnref-{key}-1" '
                    f'title="Back to reference {note.get("marker", n)} in the text" '
                    f'aria-label="Back to reference {note.get("marker", n)}">↩</a>'
                    if state["ref_seq"].get(key) else "")
            items.append(f'  <li id="fn-{key}" value="{display}"{li_style} '
                         f'data-rk="{note["rk"]}">'
                         f'{_inline(note["text"], None, None, state)}{back}</li>')
        # documents whose notes are ALL roman (i/ii/iii) keep that style on
        # the list; lettered items carry their style per-item above
        notes_ = node["notes"]
        roman = all(re.fullmatch(r"[ivxl]+", note.get("marker", "").lower())
                    for note in notes_) if notes_ else False
        ol_style = ' style="list-style-type: lower-roman"' if roman else ""
        if is_data:
            # QA-visible data layer: plain, pink-backed, labeled. Not styled as
            # the document's footnotes; this is the copy that will power
            # tooltips once the rollover JS lands.
            return (f'<div class="fn-data" {_attrs(node, pages)}>\n'
                    '  <p class="fn-data-title">Hidden data for footnotes (QA)</p>\n'
                    f'  <ol{ol_style}>\n' + "\n".join(items) + '\n  </ol>\n</div>')
        return (f'<section class="footnotes" {_attrs(node, pages)}>\n'
                f'<ol{ol_style}>\n' + "\n".join(items) + '\n</ol>\n</section>')
    ctx.log.entry("unknown-node", type=t, rk=node.get("rk"))
    return f"<!-- unrendered node type {html.escape(t)} ({node.get('rk')}) -->"


# nesting order for overlapping wrap spans: lower rank = outer wrapper, so a
# bold+italic+linked title renders <a><strong><em>…. Fixed ranks make the
# segment sweep's nesting deterministic regardless of where spans start/end.
_WRAP_RANK = {"lead": 0, "link": 1, "mark": 2, "strong": 3, "color": 3.5,
              "em": 4}


def _inline(text, links, refs, state, breaks=None, emph=None, marks=None,
            lead=None, colors=None, page=None):
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
    for s, e, hx in (colors or []):
        # emphasis-by-color (rubric §3): promoted to <strong> with a class that
        # restores the exact source color (the class neutralizes the default
        # bolding — the source colored this text, it didn't embolden it).
        # Marker glyphs (colored bullets, dingbats) carry no words — skip them.
        if _usable_color(hx) and any(ch.isalnum() for ch in text[s:e]):
            wraps.append((s, e, _WRAP_RANK["color"],
                          f'<strong class="c-{hx[1:]}">', "</strong>"))

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
                    + [(s, e) for s, e, _c in (marks or [])]
                    + [(s, e) for s, e, _c in (colors or [])])
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
            key = _resolve_fn(state, data, page) if data in state["fn_nums"] else None
            if key:
                k = state["ref_seq"].get(key, 0) + 1
                state["ref_seq"][key] = k
                # spaces inside a marker are run-split artifacts ("i i" is ii)
                marker = seg.replace(" ", "")
                mk = (f'<sup class="fnref" id="fnref-{key}-{k}">'
                      f'<a href="#fn-{key}">{marker}</a></sup>')
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
        # no anchor: reproduce the source color (webified §5.3 — blue signatory
        # names, colored cross-refs). _usable_color drops near-white (legible only
        # on the PDF's dark panels); those stay body color as before.
        col = _usable_color(payload.get("color"))
        style = f' style="color:{col}"' if col else ""
        return ("wrap", f'<span data-link-styled="true"{style}>', "</span>")
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


def _dark_callout_fg(node):
    """The source text color a DARK callout painted its contents (webified §5.4).
    _usable_color drops near-white text as unusable on the white page, so a dark
    box's own children would fall back to body black — illegible on the fill. We
    set the box's color to the dominant descendant source color when it is light,
    so light-on-dark reads as the source intended instead of black-on-dark."""
    votes = Counter()

    def walk(n):
        col = (n.get("data") or {}).get("color")
        if col:
            votes[col] += max(len(n.get("text", "") or ""), 1)
        for c in n.get("children", []):
            walk(c)

    for c in node.get("children", []):
        walk(c)
    if not votes:
        return None
    col = votes.most_common(1)[0][0]
    return col if not _dark(col) else None  # only restore genuinely light text


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


def _styleguide(ir):
    """Per-document design tokens distilled from the IR's style provenance — the
    heading scale, body type, link color, callout palette and quote style the
    document actually uses (webified §5.6). Emitted for inspection and as the
    substrate the vision loop's styleTokens (§3.5) adjust; the renderer already
    derives the same values inline for its CSS, so this is a serialization of
    what layer 3 knows, not a new computation."""
    body, heads = _style_profile(ir)
    link_votes = Counter()
    palette = Counter()
    quote = None

    def walk(n):
        nonlocal quote
        d = n.get("data") or {}
        if n.get("type") == "paragraph":
            own = _usable_color(d.get("color"))
            links = n.get("links") or []
            if links and own:
                r, g, b = (int(own[i:i + 2], 16) for i in (1, 3, 5))
                if max(r, g, b) - min(r, g, b) >= 24:  # greys aren't link styling
                    span = sum(e - s for s, e, _t in links)
                    if span >= 0.6 * max(len(n.get("text", "") or ""), 1):
                        link_votes[own] += span
        if n.get("type") == "aside":
            fill = d.get("fill")
            if fill and fill != "#ffffff":
                palette[fill] += 1
            if quote is None and (n.get("_cls") == "quote" or n.get("quoteOpen")):
                quote = {"color": d.get("color"),
                         "mark": n.get("quoteOpen")}
        for c in n.get("children", []):
            walk(c)

    for n in ir["body"]:
        walk(n)

    return {
        "body": {"font": body.get("font"), "size": body.get("size"),
                 "color": _usable_color(body.get("color")) or body.get("color")},
        "headings": {str(lv): {"font": h.get("font"), "size": h.get("size"),
                               "color": h.get("color")}
                     for lv, h in sorted(heads.items())},
        "linkColor": link_votes.most_common(1)[0][0] if link_votes else None,
        "calloutPalette": [c for c, _n in palette.most_common()],
        "quote": quote,
    }


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
    if "background:" in txt:
        traits.append("panel")
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

    # config-driven web-font mapping: a per-doc fonts.map turns a source font
    # name into a real Google/Adobe family that actually exists on a CDN (the
    # extracted name, e.g. "OxfamTSTARPRO", is on no CDN). "*" maps every font; a
    # substring key maps just the matching ones. A big, cheap fidelity boost
    # while true font embedding stays parked.
    font_cfg = (ctx.cfg.get("output") or {}).get("fonts") or {}
    fmap = font_cfg.get("map") or {}

    def _web(name, fam):
        low = (name or "").lower()
        star = None
        for k, v in fmap.items():
            if k == "*":
                star = v
            elif k.lower() in low:
                return v
        return star or fam

    def fam_value(name, fam, generic):
        """font-family value. For an embedded font, route through a CSS var that
        ONLY embed.css defines (as "PDFEmbed <family>", "<family>", generic) — so
        with the embed layer off the var() fallback here drops cleanly to the
        guessed font and the element never names the embedded face. All cuts of a
        family share one "PDFEmbed <family>" name so <strong>/<em> pick the
        bold/italic face by weight/style — emphasis works like a real font."""
        mapped = _web(name, fam)
        if mapped != fam:                  # explicit config map wins over embed
            return f'"{mapped}", {generic}'
        if name in embed:
            return f'var(--rkf-{_famkey(fam)}, "{fam}", {generic})'
        return f'"{fam}", {generic}'

    def note_family(name, fam, weight, style):
        mapped = _web(name, fam)
        if mapped == fam and name in embed:
            return  # embedded & not remapped — served locally, never fetched
        fam = mapped                        # fetch the mapped CDN family
        low = (fam or "").lower()
        if not fam or low in SYSTEM_FAMILIES or low.split()[0] in SYSTEM_FAMILIES:
            return
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
        bg = d.get("bg")
        if bg:
            # the block sits on a colored panel in the source (cover band,
            # section banner): reproduce it, and on a dark panel the near-white
            # text color _usable_color would drop becomes legible again
            rules.append(f"  background: {bg};")
            rules.append("  padding: 0.6em 0.8em;")
            if own is None and d.get("color") and _dark(bg):
                own = d["color"]
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
        # fidelity-first: reproduce even small size departures (a 9pt caption
        # against 10pt body reads differently); 5% ≈ below rounding noise
        if d.get("size") and abs(d["size"] / body_pt - 1) >= 0.05:
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

    # inline emphasis-by-color palette (rubric §3): colored non-link runs render
    # as <strong class="c-xxxxxx">; the class restores the exact source color
    # and neutralizes strong's default bolding (the source colored this text,
    # it didn't embolden it — a run that IS also bold nests inside a real
    # <strong> and inherits its weight).
    cpal = set()

    def feed_cpal(n):
        for _s, _e, hx in n.get("colors") or []:
            cpal.add(hx)
        for it in n.get("items") or []:
            if isinstance(it, dict):
                for _s, _e, hx in it.get("colors") or []:
                    cpal.add(hx)
                for si in (it.get("sub") or {}).get("items") or []:
                    if isinstance(si, dict):
                        for _s, _e, hx in si.get("colors") or []:
                            cpal.add(hx)
        for c in n.get("children", []):
            feed_cpal(c)

    for n in ir["body"]:
        feed_cpal(n)
    cpal_rules = [f"strong.c-{hx[1:]} {{ color: {hx}; font-weight: inherit; }}"
                  for hx in sorted(cpal) if _usable_color(hx)]
    if cpal_rules:
        out += cpal_rules + [""]

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
    # the column) their floated position and width; floated figures too.
    # Walk RECURSIVELY: nested nodes (columns cells, aside children) carry the
    # same per-node styling provenance — a top-level-only loop silently
    # unstyles anything grouping passes have wrapped (the edf p6 drop cap).
    def _iter_nodes(ns):
        for n in ns:
            yield n
            yield from _iter_nodes(n.get("children", []))

    for n in _iter_nodes(ir["body"]):
        d = n.get("data") or {}
        if n["type"] == "paragraph" and d.get("dropCap"):
            # ornamental drop cap (rubric §3: preserve via CSS by default).
            # data.dropCap = "<scale> <#hex>": scale = cap size / body size.
            # ~0.65× the print scale spans about the same lines on the web
            # (web line-height is looser than print leading). Floor 1.1em:
            # even a modest oversized lead letter (chep's 1.9× labels) is a
            # real design flourish — render it proportionally.
            try:
                parts_dc = d["dropCap"].split()
                dc_size = round(float(parts_dc[0]) * 0.65, 2)
                dc_color = parts_dc[1]
                dc_weight = parts_dc[2] if len(parts_dc) > 2 else None
            except (ValueError, AttributeError, IndexError):
                dc_size, dc_color, dc_weight = None, None, None
            if dc_size and dc_size >= 1.1:
                rules_dc = [f"  float: left;",
                            f"  font-size: {dc_size}em;",
                            "  line-height: 0.8;",
                            "  padding: 0.04em 0.08em 0 0;"]
                if dc_weight:
                    # the cap's TRUE weight — also shields it from inheriting
                    # a <strong> the paragraph happens to open with
                    rules_dc.append(f"  font-weight: {dc_weight};")
                if _usable_color(dc_color):
                    rules_dc.append(f"  color: {dc_color};")
                out += [f'[data-nid="{n["nid"]}"]::first-letter {{',
                        *rules_dc, "}", ""]
        if n["type"] == "heading":
            # heading whose own color differs from its level's dominant color;
            # a heading on a colored panel (cover band) also reproduces the
            # panel, which un-drops its light text color
            lv_color = heads.get(n["level"], {}).get("color")
            own = _usable_color(d.get("color"))
            bg = d.get("bg")
            h_rules = []
            on_dark = False
            if bg:
                h_rules += [f"  background: {bg};", "  padding: 0.4em 0.6em;"]
                if own is None and d.get("color") and _dark(bg):
                    own = d["color"]
                    on_dark = True
            # a near-white color restored on a dark panel is NEVER carried by the
            # level-wide h-rule (_usable_color drops white there), so emit it even
            # when it equals the level's dominant color — else the heading falls
            # back to body black on its dark band (§5.4 — clean-air p15 banner)
            if own and (on_dark or own != (lv_color if lv_color else None)):
                h_rules.append(f"  color: {own};")
            if h_rules:
                out += [f'[data-nid="{n["nid"]}"] {{', *h_rules, "}", ""]
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
        dark_fg = None
        if n["type"] == "aside":
            if d.get("fill") and d["fill"] not in ("#ffffff",):
                rules.append(f"  background: {d['fill']};")
                # dark callout: restore the light source text color its children
                # carried (dropped by _usable_color) so they read light-on-dark,
                # not body-black-on-dark (§5.4 — good-food p22 Conclusion box)
                if _dark(d["fill"]):
                    dark_fg = _dark_callout_fg(n)
                    if dark_fg:
                        rules.append(f"  color: {dark_fg};")
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
        # links/headings inside a dark callout otherwise take the doc link/heading
        # color (dark) and go illegible; the source painted them light like the
        # rest of the box, so force the restored color on them too (§5.4)
        if dark_fg:
            out += [f'[data-nid="{n["nid"]}"] a, '
                    f'[data-nid="{n["nid"]}"] h1, [data-nid="{n["nid"]}"] h2, '
                    f'[data-nid="{n["nid"]}"] h3, [data-nid="{n["nid"]}"] h4, '
                    f'[data-nid="{n["nid"]}"] h5, [data-nid="{n["nid"]}"] h6 '
                    f'{{ color: {dark_fg}; }}', ""]

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
    for url in (font_cfg.get("load") or []):     # Adobe kits / explicit sheets
        imports.insert(0, f'@import url("{url}");')
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
