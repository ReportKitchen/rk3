"""Analyze stage: classify blocks + graphic objects into document structure
and emit the IR.

Structure handled here: headings (font-size clustering normalized to h1..h6),
paragraphs (dehyphenated), bulleted lists, figures (graphics-dense regions
cropped from the page PNGs, with caption detection), and callouts
(filled/bordered boxes whose text becomes <aside> children). Tables and
footnotes land in milestone 4.

Artifact: ir.json
  { "title", "body": [ node... ] }
  node types: heading {level,text,id} | paragraph {text,strong?} | list {items}
            | figure {src,width,height,caption?,alt} | aside {children:[node]}
  every node: { "page", "bbox", "rk", "nid", "data": {provenance} }

`nid` is a *stable* node id (hash of type+page+bbox): unlike the per-run rk
debug keys, nids survive re-runs, so viewer feedback, question answers, and
future edit operations can target nodes durably.

ir.json also carries "questions": low-confidence decisions surfaced to the
user as (?) markers in the viewer:
  { "qid", "nid", "page", "kind", "prompt", "options": [..], "chosen" }
qid is content-derived (stable across re-runs) for the same reason.
"""

import hashlib
import re
from collections import Counter

from PIL import Image

VERSION = 137


# PDF font-descriptor flag bits
# emphasis is judged on the TRUE weight/slant that extract read from each
# embedded font program (rk3.engines.pdfium.fontid) — the deterministic identity
# the renderer itself uses, not a guess from the flattened /BaseFont name or
# glyph widths. A run is bold when it's at least EMPH_GAP heavier than the block
# baseline (a real weight step is ~80+; a same-cut subset difference is ~0).
EMPH_GAP = 50


def _font_is_italic(f):
    return bool(f.get("italic"))


def _font_weight_rank(f):
    return f.get("weight", 400)

OL_RE = re.compile(r"^(\d{1,2}|[A-Za-z])\s?[.)]\s+")


def _ol_marker(text):
    """Ordinal list marker: ('decimal'|'lower-alpha'|'upper-alpha', n, end)."""
    m = OL_RE.match(text)
    if not m:
        return None
    raw = m.group(1)
    if raw.isdigit():
        return "decimal", int(raw), m.end()
    style = "upper-alpha" if raw.isupper() else "lower-alpha"
    return style, ord(raw.lower()) - 96, m.end()


def _alnum(text):
    return sum(1 for ch in (text or "") if ch.isalnum())


def _hex(rgba):
    return "#{:02x}{:02x}{:02x}".format(*rgba[:3])


def _override_for(overrides, text):
    low = text.lower()
    for ov in overrides:
        p = ov.get("textPrefix", "")
        if p and low.startswith(p.lower()):
            return ov
    return None

ROMAN = {}
for _n, _r in enumerate(
        "i ii iii iv v vi vii viii ix x xi xii xiii xiv xv xvi xvii xviii xix xx"
        .split(), start=1):
    ROMAN[_r] = _n


# alphabetic footnote designators (a, b, c … as used for table notes) live in
# their own namespace above any realistic numeric note count, so a doc using
# BOTH numbered endnotes and lettered table-notes can't cross-wire refs
_ALPHA_NOTE_BASE = 1000
# a forward gap this small is accepted outright (a note or two genuinely
# missing). BIGGER jumps are accepted only if a one-step lookahead shows the
# sequence continuing FROM the jump — otherwise the jump is a misread outlier
# and the true next note resumes near where we were. See _accept_marker.
_NOTE_SMALLGAP = 3


def _marker_value(raw):
    """Footnote marker -> int (arabic, roman, or single letter), else None.
    Letters map to _ALPHA_NOTE_BASE+1… ('a'=1001); i/v/x stay roman — an
    alphabetic series crossing 'i' loses that one marker (logged upstream as a
    sequence break), which beats misreading roman notes as letters."""
    raw = raw.strip().rstrip(".)").strip()
    if raw.isdigit() and len(raw) <= 3:
        return int(raw)
    rv = ROMAN.get(raw.lower())
    if rv:
        return rv
    if len(raw) == 1 and raw.isalpha():
        return _ALPHA_NOTE_BASE + ord(raw.lower()) - 96
    return None

# function words that mark a WRAPPED clause when they END a candidate run-in
# heading (a heading ends on a content word; "…points for" / "…already in the"
# is a sentence fragment or a truncated multi-line heading we must not promote)
_LEAD_STOPWORDS = frozenset((
    "a an the and or but nor for of to in on at by with from as into than then so "
    "is are was were be been that this these those which who whom will would can could "
    "may might about over under between per via up out our their its your we you they it if when while "
    "any many both several each every another"
).split())

BULLETS = "•◦▪‣–—-*·§◊♦►▸✦➤●○"
# bullets that count as list markers when sitting INSIDE a line of text — the
# narrow set, excluding -–—*·§ which are overwhelmingly hyphens/wrap-dashes
# mid-sentence, not list markers (an interior '-' must never split a paragraph)
INLINE_BULLETS = "•◦▪‣●○■□▸►◆◇♦❖➤"
OBJ_PATH, OBJ_IMAGE, OBJ_SHADING = 2, 3, 4
# objects: [type, l, b, r, t, fillIdx, strokeIdx, filled, stroked]
OT, OL, OB, OR_, OTOP = range(5)


def _norm_text(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())[:60]


def _stable_id(prefix, used, kind, page, bbox, text=None):
    """Durable ids: hashed on normalized text when the node has text (immune
    to bbox drift from layout fixes), coarse 10pt-grid bbox otherwise."""
    if text and _norm_text(text):
        raw = f"{kind}|{page}|{_norm_text(text)}"
    else:
        raw = f"{kind}|{page}|" + ",".join(str(round(v / 10)) for v in bbox)
    base = prefix + hashlib.sha1(raw.encode()).hexdigest()[:10]
    sid, i = base, 1
    while sid in used:
        i += 1
        sid = f"{base}-{i}"
    used.add(sid)
    return sid


class InfoLossError(Exception):
    """A list item lost its style runs (it's a bare string). Raised loudly
    rather than shipping a silent emphasis/link drop - see [[surface-failures]]
    and the information-monotonicity doctrine in [[foundation-legs]]."""


def _leaf(ctx, type_, runs, page, bbox, rk, data=None, **extra):
    """Build a text LEAF node — the single funnel from a runs-dict to a node.
    Every inline run in _RUN_KEYS present on `runs` is attached here, so no
    construction path can hand-roll a node and silently drop emphasis/links/
    sups again (first-class content: any text node holds any inline feature).
    Every leaf gets a durable nid, so it is addressable by ops/feedback."""
    node = {"type": type_, "text": runs.get("text", ""), "page": page,
            "bbox": bbox, "rk": rk}
    if data is not None:
        node["data"] = data
    for k in _RUN_KEYS:
        if runs.get(k):
            node[k] = runs[k]
    node.update(extra)
    node["nid"] = _stable_id("n", ctx.nids, type_, page, bbox, node["text"])
    return node


def _container(ctx, type_, children, page, bbox, rk, data=None, **extra):
    """Build a CONTAINER node: an ordered list of child nodes and nothing
    else. One containment rule for the whole IR — any node can appear inside
    any container, so a cell holds a figure (or a caption holds an aside)
    tomorrow with zero new plumbing. A container never stores raw text of its
    own; text lives in a leaf child."""
    node = {"type": type_, "children": children, "page": page, "bbox": bbox,
            "rk": rk}
    if data is not None:
        node["data"] = data
    node.update(extra)
    node["nid"] = _stable_id("n", ctx.nids, type_, page, bbox,
                             "|".join(c["nid"] for c in children))
    return node


def _assert_nids(nodes):
    """Unified-model invariant: every typed node anywhere in the tree carries
    a durable nid (addressable by ops/feedback). A missing nid means some
    builder bypassed the _leaf/_container constructors."""
    def walk(u):
        if isinstance(u, dict):
            if u.get("type") and not u.get("nid"):
                yield u
            for v in u.values():
                if isinstance(v, (dict, list)):
                    yield from walk(v)
        elif isinstance(u, list):
            for v in u:
                yield from walk(v)
    bad = list(walk(nodes))
    if bad:
        raise InfoLossError(
            f"{len(bad)} typed node(s) without a nid; first: "
            f"{str(bad[0])[:140]}")


def _assert_rich_items(nodes):
    """No-loss guard (information monotonicity): every list item and sub-item
    must be a rich dict built by slicing a source node's runs. A bare string
    means some construction path re-derived text from scratch and DROPPED its
    emphasis/links/marks - a class of silent loss we make impossible by failing
    here instead. Recurses into child-bearing nodes (deflists, regions)."""
    def walk(ns):
        for n in ns:
            if n.get("type") == "list":
                for it in n.get("items", []):
                    if not isinstance(it, dict):
                        yield n, it
                        continue
                    for s in (it.get("sub") or {}).get("items", []):
                        if not isinstance(s, dict):
                            yield n, s
            if n.get("children"):
                yield from walk(n["children"])
    bad = list(walk(nodes))
    if bad:
        where = "; ".join(f"{n.get('rk')}:{str(it)[:40]!r}" for n, it in bad[:5])
        raise InfoLossError(
            f"{len(bad)} list item(s) reduced to bare strings (style dropped): "
            f"{where}")


def run(ctx):
    asm = ctx.artifact("assemble")
    blocks, fonts, colors = asm["blocks"], asm["fonts"], asm["colors"]
    pages = {p["n"]: p for p in asm["pages"]}
    ctx.page_h = {p["n"]: p["height"] for p in asm["pages"]}
    ctx.page_dims = {p["n"]: (p["width"], p["height"]) for p in asm["pages"]}
    ctx.page_objs = {p["n"]: p.get("objects", []) for p in asm["pages"]}
    ctx.colors = colors
    ctx.questions = []
    ctx.nids = set()
    ctx.qids = set()
    # text accounting: every alnum char entering this stage must leave in the
    # output or be claimed by a logged removal; the audit (in ir.json) makes
    # silent content loss a test failure instead of a user discovery
    ctx.audit_claimed = Counter()
    ctx.audit_moved = Counter()

    ctx.fonts = fonts
    link_colors = _link_colors(ctx, blocks)
    rich = [_join_block(ctx, blk, link_colors) for blk in blocks]
    texts = [r["text"] for r in rich]
    body_size = _body_size(ctx, blocks)
    roles = _block_roles(pages, blocks)  # (role, coverage) per block, tag docs only
    tag_levels = _tag_heading_levels(ctx, roles)

    drop_toc = ctx.cfg["structure"].get("dropToc", True)
    toc_bands = _toc_pages(ctx, pages, blocks) if drop_toc else {}
    skip = set()
    for i, blk in enumerate(blocks):
        band = toc_bands.get(blk["page"])
        if band and band[0] <= (blk["bbox"][1] + blk["bbox"][3]) / 2 <= band[1]:
            skip.add(i)
    for i in skip:
        ctx.log.entry("toc-drop", page=blocks[i]["page"], block=blocks[i]["rk"],
                      text=texts[i][:60])
        ctx.audit_claimed[blocks[i]["page"]] += _alnum(texts[i])
    for i, blk in enumerate(blocks):
        if i in skip:
            continue
        role, cov = roles[i]
        if role == "Artifact" and cov > 0.5:
            # authors mis-tag whole designed pages as Artifact; trust the tag
            # only where decoration lives — page edges or short snippets.
            # Substantial mid-page text is content regardless of the tag —
            # and so are FOOTNOTES (marker + citation signal) and a notes
            # heading: tenure tags its END NOTES page Artifact, which was
            # silently deleting notes d and e (real content loss).
            page = pages[blk["page"]]
            edge = (blk["bbox"][1] < 0.12 * page["height"]
                    or blk["bbox"][3] > 0.88 * page["height"])
            nm = _line_marker(blk["lines"][0])
            # a note = leading marker + citation signal, or a leading
            # SUPERSCRIPT marker (unambiguous even without a URL/year in this
            # block — the citation may sit in a continuation fragment)
            noteish = ((nm and (nm[3] or _CITE_RE.search(texts[i])))
                       or NOTES_HEADING.fullmatch(texts[i].strip()))
            if (edge or len(texts[i]) <= 80) and not noteish:
                skip.add(i)
                ctx.log.entry("strip-artifact", page=blk["page"], block=blk["rk"],
                              coverage=round(cov, 2), text=texts[i][:60])
                ctx.audit_claimed[blk["page"]] += _alnum(texts[i])
            else:
                ctx.log.entry("artifact-kept", page=blk["page"], block=blk["rk"],
                              chars=len(texts[i]), text=texts[i][:60],
                              reason="Artifact-tagged but substantial mid-page text")
        elif drop_toc and role in ("TOC", "TOCI") and cov > 0.5:
            skip.add(i)
            ctx.log.entry("toc-tag-drop", page=blk["page"], block=blk["rk"],
                          text=texts[i][:60])

    top_size = max((_dominant_size(b) for b in blocks), default=body_size)
    regions = _detect_regions(ctx, pages, blocks, texts, body_size, toc_bands,
                              top_size)
    regions = _merge_cross_page_callouts(ctx, regions, pages)
    absorbed = {}  # block index -> region
    for reg in regions:
        for bi in reg["blockIdx"]:
            absorbed[bi] = reg
    _find_captions(ctx, regions, blocks, texts, absorbed, body_size, roles)
    absorbed.update(dict.fromkeys(skip))

    # Notes hide inside regions too: gates prints section endnotes inside its
    # chart figures (112-115, 300, 338); atlantic sets note 5 in a sidebar
    # callout. A region-absorbed block that is NOTE-SHAPED — leading marker
    # plus a citation signal, or a superscript marker — stays eligible for
    # note collection. It still belongs to its region for body building (a
    # figure keeps it inside the crop, an aside keeps its text); collection
    # only adds the fielded note so its references reconcile. Chart legends
    # ("2 Livestock,") and numbered list items ("5. Meaningfully advancing…")
    # fail the citation gate and stay skipped.
    note_skip = set()
    for bi, reg in absorbed.items():
        if reg is not None and _noteish_block(blocks[bi], texts[bi]):
            continue
        note_skip.add(bi)
    notes, note_idx, notes_place = _find_notes(ctx, pages, blocks, texts,
                                                 note_skip, body_size)
    absorbed.update(dict.fromkeys(note_idx))

    main_idx = [i for i in range(len(blocks)) if i not in absorbed]
    levels = _heading_levels(ctx, [blocks[i] for i in main_idx],
                             [texts[i] for i in main_idx], body_size)

    # weave figure/callout regions into the block flow by vertical position;
    # pages with a clear two-column layout get column-aware reading order
    # (left column top-down, then right), banded by full-width elements
    page_items = {}
    for i in main_idx:
        page_items.setdefault(blocks[i]["page"], []).append(("block", i))
    for reg in regions:
        items = page_items.setdefault(reg["page"], [])
        pos = len(items)
        for k, (kind, ref) in enumerate(items):
            if kind == "block" and blocks[ref]["bbox"][3] < reg["bbox"][3]:
                pos = k
                break
        items.insert(pos, ("region", reg))

    def item_bbox(item):
        kind, ref = item
        return blocks[ref]["bbox"] if kind == "block" else ref["bbox"]

    # Reading order, per page. For a reliably-tagged page the DECLARED order (the
    # struct tree's depth-first sequence — authoritative per ISO 32000-2 §14.7)
    # wins; items the tags don't cover are slotted in by geometry. Otherwise we
    # infer it geometrically (_side_rows + XY-cut). See docs/research/reading-order.md
    twocol_pages = set()
    ro_src = Counter()  # per-page reading-order source -> doc tagging verdict
    for page_n, items in page_items.items():
        tagged = pages[page_n].get("tagged", [])
        struct = [_struct_order(tagged, item_bbox(it)) for it in items]
        tagged_frac = (sum(1 for o in struct if o >= 0) / len(items)) if items else 0.0
        # ncols is still read geometrically (drives aside/pull-quote layout)
        geom_order, ncols = _reading_order([item_bbox(it) for it in items])
        if tagged_frac >= 0.6:
            # declared order; untagged items interpolate right after the tagged
            # item that geometrically precedes them (stable sub-order via `frac`)
            keys, last, frac = {}, -1, 0
            for gi in geom_order:
                if struct[gi] >= 0:
                    keys[gi], last, frac = (struct[gi], 0), struct[gi], 0
                else:
                    frac += 1
                    keys[gi] = (last, frac)
            order = sorted(range(len(items)), key=lambda k: keys[k])
            src = "struct-tree"
        else:
            grouped = _side_rows(ctx, items, blocks, body_size, page_n)
            if grouped is not None:
                items = grouped
                geom_order, ncols = _reading_order([item_bbox(it) for it in items])
                order = geom_order
            else:
                # heading-left/body-right rows return a flat list already in
                # reading order — don't re-run the XY-cut (it would re-derive the
                # column-major order this is here to override)
                aside = _heading_aside_rows(ctx, items, blocks, body_size, page_n)
                if aside is not None:
                    items, order = aside, list(range(len(aside)))
                else:
                    order = geom_order
            src = "geometry"
        page_items[page_n] = [items[k] for k in order]
        if ncols >= 2:
            twocol_pages.add(page_n)
        if items:
            ro_src[src] += 1
        ctx.log.entry("reading-order", page=page_n, columns=ncols,
                      items=len(items), source=src,
                      tagged=round(tagged_frac, 2))

    deepest = max([*tag_levels.values(), *levels.values(), 0])
    kicker_level = min(deepest + 1, 6) if deepest else 0

    nodes = []
    used_ids = set()
    fig_count = 0

    def _build_item(kind, ref):
        nonlocal fig_count
        if kind == "block":
            return _block_node(ctx, blocks[ref], rich[ref], fonts,
                               levels, body_size, used_ids,
                               role=roles[ref], tag_levels=tag_levels,
                               kicker_level=kicker_level)
        if ref["kind"] == "figure":
            # grid-ruled, text-dense "figures" are tables (strict gate keeps
            # charts with gridlines out); the region stops claiming its text
            node = _try_table(ctx, ref, blocks, rich, pages, strict=True)
            if node is not None:
                ref["kind"] = "table"
            else:
                fig_count += 1
                node = _figure_node(ctx, ref, pages, fig_count, blocks, rich)
        else:
            node = _try_table(ctx, ref, blocks, rich, pages)
            if node is None:
                node = _aside_node(ctx, ref, blocks, rich, fonts,
                                   body_size, roles)
                fig_count = _aside_images(ctx, ref, node, pages,
                                          fig_count)
        if ref.get("uncertain") and node["type"] != "table":
            prompt = (
                "This region is currently a cropped figure image, but it "
                "contains a lot of text. Make it a callout with real, "
                "selectable text instead?"
                if ref["kind"] == "figure" else
                "This region is currently a callout (styled text box). "
                "Should it be a cropped image of the original region "
                "instead?")
            _question(ctx, "figure-or-callout", node, prompt,
                      ["figure", "callout"], ref["kind"])
        if ref.get("captionWeak") and ref.get("caption"):
            _question(ctx, "caption", node,
                      f"Is “{ref['caption'][:60]}” a caption for this "
                      "figure, or an ordinary paragraph?",
                      ["caption", "paragraph"], "caption")
        return node

    for page_n in sorted(page_items):
        for kind, ref in page_items[page_n]:
            if kind == "row":
                children = []
                for ci, cell in enumerate(ref["cells"]):
                    for k2, r2 in cell:
                        child = _build_item(k2, r2)
                        child["cell"] = ci
                        children.append(child)
                nodes.append({
                    "type": "columns", "children": children,
                    "page": page_n, "bbox": ref["bbox"], "rk": ref["rk"],
                    "nid": _stable_id("n", ctx.nids, "columns", page_n,
                                      ref["bbox"],
                                      "|".join(c["nid"] for c in children))})
            else:
                nodes.append(_build_item(kind, ref))

    # figure regions absorb their text into the cropped image
    for reg in regions:
        if reg["kind"] == "figure":
            for bi in reg["blockIdx"]:
                ctx.audit_claimed[blocks[bi]["page"]] += _alnum(texts[bi])

    nodes = _promote_lead_headings(ctx, nodes, used_ids)
    nodes = _split_inline_bullets(ctx, nodes)
    nodes = _group_tag_lists(ctx, nodes)
    nodes = _group_bullet_paragraphs(ctx, nodes)
    # sentences interrupted by page breaks happen in the main flow too,
    # not just inside callouts
    nodes = _join_pagebreak_sentences(ctx, nodes)
    nodes = _join_column_wrap(ctx, nodes)
    nodes = _join_broken_paragraphs(ctx, nodes)
    nodes = _merge_crosspage_lists(ctx, nodes)
    nodes = _merge_crosspage_bullet_lists(ctx, nodes)
    nodes = _marker_lists(ctx, nodes)
    nodes = _definition_lists(ctx, nodes)
    nodes = _floating_pullquotes(ctx, nodes, body_size)
    nodes = _aside_layout_and_pullquotes(ctx, nodes, twocol_pages)
    # a second pass: paragraphs that a floating pullquote/aside sat between are
    # now adjacent (the intruder has been extracted) — rejoin the split sentence
    nodes = _join_broken_paragraphs(ctx, nodes)
    _indents(ctx, nodes)
    # information-monotonicity guard: list construction is complete; every item
    # must now be a rich dict (a bare string would be a silent style drop)
    _assert_rich_items(nodes)

    # unified container model: lists leave the passes' working shape (items:
    # runs-dicts) and become item containers holding leaf children, so render/
    # ops/refs/audit see one shape and any content can nest inside an item
    nodes = _upgrade_lists(ctx, nodes)

    # flood guard: questionnaire-style documents raise the same per-block
    # question hundreds of times (the survey: 174 figure-or-callout, 131
    # hard-returns). Past 50 the panel keeps the first of that kind; the
    # per-block lever is config. Stopgap until question grouping lands -
    # the bar is high so living queues (facilitator ~40) are untouched.
    for kind in ("hard-returns", "figure-or-callout"):
        flood = [q for q in ctx.questions if q["kind"] == kind]
        if len(flood) > 50:
            keep = flood[0]["qid"]
            ctx.questions = [q for q in ctx.questions
                             if q["kind"] != kind or q["qid"] == keep]
            ctx.log.entry("question-flood", kind=kind,
                          suppressed=len(flood) - 1)

    typed = [n for n in nodes if (n.get("data") or {}).get("pitch")]
    if len(typed) >= 5:
        # one document-level choice, anchored at the first joined paragraph
        mode = ctx.cfg["structure"].get("typedLines", "join")
        ctx.log.entry("typed-lines", paragraphs=len(typed), mode=mode)
        _question(ctx, "typed-lines", typed[0],
                  f"This document hard-types its line breaks ({len(typed)} "
                  "paragraphs were joined from typed lines, document-wide). "
                  "Join them into flowing paragraphs, or preserve the "
                  "original line breaks?",
                  ["join into paragraphs", "preserve line breaks"],
                  "join into paragraphs" if mode == "join"
                  else "preserve line breaks")

    if notes:
        last = blocks[max(note_idx)]
        rk = ctx.log.entry("footnotes", count=len(notes),
                           numbers=[n["n"] for n in notes][:20],
                           placed=notes_place is not None)
        # Two copies (user spec): an IN-PLACE styled copy at the notes' own
        # location (where the content was found), and a DATA copy at the very
        # end — plain, QA-visible, carrying the ref<->note linkage attributes.
        if notes_place is not None:
            first = notes_place
            inline = {"type": "footnotes", "variant": "inline", "notes": notes,
                      "page": blocks[first]["page"], "bbox": blocks[first]["bbox"],
                      "rk": rk, "data": {}}
            inline["nid"] = _stable_id("n", ctx.nids, "footnotes",
                                       inline["page"], inline["bbox"], "footnotes")
            key = (blocks[first]["page"], -blocks[first]["bbox"][3])
            pos = next((k for k, n in enumerate(nodes)
                        if (n["page"], -n["bbox"][3]) > key), len(nodes))
            nodes.insert(pos, inline)

        data = {"type": "footnotes", "variant": "data", "notes": notes,
                "page": last["page"], "bbox": last["bbox"], "rk": rk, "data": {}}
        data["nid"] = _stable_id("n", ctx.nids, "footnotes-data",
                                 data["page"], data["bbox"], "footnotes-data")
        nodes.append(data)

    # References are a property of text, not of paragraphs: attach them to every
    # text unit (list items, table cells, …) from its superscripts, in one place.
    _attach_refs(nodes)

    # Reconciliation flag (user QA): every in-text reference index should have a
    # matching note and vice-versa. Mismatches (both directions) surface as a
    # banner at the TOP of the document until there's a dedicated flags panel.
    flag = _reconcile_notes(ctx, nodes, notes)
    if flag is not None:
        nodes.insert(0, flag)

    # unified-model invariant: every typed node, at any depth, is addressable
    _assert_nids(nodes)

    title = next((n["text"] for n in nodes if n["type"] == "heading" and n["level"] == 1),
                 ctx.source.stem)
    audit = _audit(ctx, blocks, texts, nodes)
    ctx.write_artifact("analyze", {
        "title": title,
        "warnings": ctx.artifact("extract").get("warnings", []),
        "pages": {str(p["n"]): [p["width"], p["height"]] for p in asm["pages"]},
        "questions": ctx.questions,
        "audit": audit,
        "fonts_embed": asm.get("embeddedFonts", {}),
        "fonts_complete": asm.get("fontsComplete", True),
        "tagged": _tag_verdict(ro_src),
        "body": nodes,
    })


def _audit(ctx, blocks, texts, nodes):
    audit_in = Counter()
    for blk, text in zip(blocks, texts):
        audit_in[blk["page"]] += _alnum(text)

    out = Counter()

    def count_node(n):
        page = n["page"]
        out[page] += _alnum(n.get("text"))
        out[page] += sum(_alnum(t) for t in _item_texts(n.get("items", [])))
        out[page] += _alnum(n.get("caption"))
        out[page] += _alnum(n.get("title"))
        out[page] += _alnum(n.get("sectionNum"))
        for note in n.get("notes", []):
            out[note.get("page", page)] += _alnum(note["text"]) \
                + _alnum(note.get("marker"))
        for c in n.get("children", []):
            count_node(c)

    for n in nodes:
        count_node(n)

    pages = {}
    total_in = total_lost = 0
    for p in sorted(audit_in):
        i, o = audit_in[p], out.get(p, 0)
        c, m = ctx.audit_claimed.get(p, 0), ctx.audit_moved.get(p, 0)
        lost = max(0, i - o - c - m)
        pages[str(p)] = {"in": i, "out": o, "claimed": c, "moved": m,
                         "lost": lost}
        total_in += i
        total_lost += lost
        if lost > max(60, 0.05 * i):
            ctx.log.entry("audit-loss", page=p, **pages[str(p)])
    return {"pages": pages, "totalIn": total_in, "totalLost": total_lost}


def _question(ctx, kind, node, prompt, options, chosen):
    # derived from the (text-stable) nid so questions inherit its durability
    base = "q" + hashlib.sha1(f"{kind}|{node['nid']}".encode()).hexdigest()[:10]
    qid, i = base, 1
    while qid in ctx.qids:
        i += 1
        qid = f"{base}-{i}"
    ctx.qids.add(qid)
    ctx.questions.append({"qid": qid, "nid": node["nid"], "page": node["page"],
                          "kind": kind, "prompt": prompt, "options": options,
                          "chosen": chosen})
    ctx.log.entry("question", qid=qid, nid=node["nid"], kind=kind,
                  chosen=chosen, prompt=prompt)


# ---------------------------------------------------------------- regions ---

def _detect_regions(ctx, pages, blocks, texts, body_size, toc_pages=(),
                    top_size=None):
    """Cluster graphic objects per page, classify clusters as figure/callout."""
    repeated = _repeated_images(pages)
    regions = []
    for page in pages.values():
        if page["n"] in toc_pages:
            continue
        w, h = page["width"], page["height"]
        page_area = w * h
        graphics = []
        for o in page.get("objects", []):
            area = max(0.0, (o[OR_] - o[OL])) * max(0.0, (o[OTOP] - o[OB]))
            if area > 0.85 * page_area:
                continue  # full-page background
            if o[OT] == OBJ_IMAGE and _okey(page["n"], o) in repeated:
                ctx.log.entry("strip-decoration", page=page["n"],
                              bbox=o[OL:OTOP + 1], reason="same image bbox repeats across pages")
                continue
            if o[OT] == OBJ_PATH and (o[OR_] - o[OL]) < 3 and (o[OTOP] - o[OB]) < 3:
                continue  # dots / artifacts
            graphics.append(o)

        for cluster in _cluster(graphics):
            reg = _classify_cluster(ctx, page, cluster, blocks, texts,
                                    body_size, top_size)
            if reg:
                regions.append(reg)
            elif len(cluster["objs"]) > 1 and _too_big(cluster["bbox"], w, h):
                # adjoining layout rects (sidebar + title band) merge into a
                # page-sized cluster; re-split with overlap-only proximity and
                # classify the pieces individually
                for sub in _cluster(cluster["objs"], gap=-2.0):
                    reg = _classify_cluster(ctx, page, sub, blocks, texts,
                                            body_size, top_size)
                    if reg:
                        regions.append(reg)
    return regions


def _too_big(bbox, w, h):
    return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) > 0.9 * w * h


def _overlap_frac(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area_a = max((a[2] - a[0]) * (a[3] - a[1]), 1.0)
    return (ix * iy) / area_a


def _okey(page_n, o):
    return (round(o[OL]), round(o[OB]), round(o[OR_]), round(o[OTOP]))


def _repeated_images(pages):
    seen = Counter()
    for page in pages.values():
        for o in page.get("objects", []):
            if o[OT] == OBJ_IMAGE:
                seen[_okey(0, o)] += 1
    min_repeats = max(3, round(0.4 * len(pages)))
    return {k for k, n in seen.items() if n >= min_repeats}


def _cluster(objs, gap=8.0):
    """Merge graphic bboxes that overlap or sit within `gap` pts of each other."""
    clusters = [{"bbox": o[OL:OTOP + 1], "objs": [o]} for o in objs]
    changed = True
    while changed:
        changed = False
        out = []
        while clusters:
            cur = clusters.pop()
            for other in clusters:
                if _near(cur["bbox"], other["bbox"], gap):
                    other["bbox"] = _union(cur["bbox"], other["bbox"])
                    other["objs"].extend(cur["objs"])
                    changed = True
                    break
            else:
                out.append(cur)
        clusters = out
    return clusters


def _near(a, b, gap):
    return not (a[2] + gap < b[0] or b[2] + gap < a[0] or
                a[3] + gap < b[1] or b[3] + gap < a[1])


def _union(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def _classify_cluster(ctx, page, cluster, blocks, texts, body_size, top_size=None):
    bbox = cluster["bbox"]
    w, h = page["width"], page["height"]
    if _too_big(bbox, w, h):
        return None
    if bbox[3] - bbox[1] < 20 or bbox[2] - bbox[0] < 40:
        return None  # rules/dividers can't be regions
    n_images = sum(1 for o in cluster["objs"] if o[OT] == OBJ_IMAGE)
    n_shade = sum(1 for o in cluster["objs"] if o[OT] == OBJ_SHADING)
    n_paths = sum(1 for o in cluster["objs"] if o[OT] == OBJ_PATH)

    inside, big_inside = [], []
    for i, blk in enumerate(blocks):
        if blk["page"] != page["n"]:
            continue
        cx = (blk["bbox"][0] + blk["bbox"][2]) / 2
        cy = (blk["bbox"][1] + blk["bbox"][3]) / 2
        if bbox[0] <= cx <= bbox[2] and bbox[1] <= cy <= bbox[3]:
            size = _dominant_size(blk)
            # big text over a graphic (hero titles) stays in the text flow,
            # unless it is a numeric label (chart values)
            if size > 1.25 * body_size and not _is_label(texts[i]):
                big_inside.append(i)
            else:
                inside.append(i)

    chars_inside = sum(len(texts[i]) for i in inside)
    graphic = n_images >= 1 or n_shade >= 1 or n_paths >= 6
    boxed = 1 <= n_paths <= 5 and any(
        o[OT] == OBJ_PATH and (o[7] or o[8]) for o in cluster["objs"])

    # dominant fill/stroke of the region's boxes: layer-3 styling provenance
    fills = [(o[5], (o[3] - o[1]) * (o[4] - o[2])) for o in cluster["objs"]
             if o[OT] == OBJ_PATH and o[7] and o[5] is not None]
    strokes = [(o[6], (o[3] - o[1]) * (o[4] - o[2])) for o in cluster["objs"]
               if o[OT] == OBJ_PATH and o[8] and o[6] is not None]
    style = {}
    if fills:
        style["fillIdx"] = max(fills, key=lambda x: x[1])[0]
    if strokes:
        style["strokeIdx"] = max(strokes, key=lambda x: x[1])[0]
    borders = _region_borders(cluster, bbox)
    if borders:
        style["borders"] = borders

    # a page-bottom cluster whose only text is small note-marker lines is a
    # footnote with decoration (separator rule, highlighter fills) - the
    # notes pass owns it, not a callout
    if inside and bbox[3] < 0.2 * h:
        blks = [blocks[i] for i in inside]
        if all(_dominant_size(b) <= 0.92 * body_size for b in blks) \
                and _line_marker(blks[0]["lines"][0]):
            ctx.log.entry("region-footnote-skip", page=page["n"],
                          bbox=[round(v, 1) for v in bbox])
            return None

    # user answers (region overrides from config) trump every heuristic
    for ov in ctx.cfg["structure"].get("regionOverrides", []):
        if ov.get("page") == page["n"] and _overlap_frac(bbox, ov["bbox"]) > 0.5:
            kind = ov["kind"]
            if kind == "text":
                # dissolve: the box is page decoration, its text is ordinary
                # flow (no region, no aside, no crop)
                ctx.log.entry("region-dissolved", page=page["n"],
                              bbox=[round(v, 1) for v in bbox],
                              reason="config regionOverride (user answer)")
                return None
            rk = ctx.log.entry(kind, page=page["n"],
                               bbox=[round(v, 1) for v in bbox],
                               reason="config regionOverride (user answer)")
            absorbed_idx = (inside if kind == "figure"
                            else sorted(inside + big_inside))
            return {"kind": kind, "page": page["n"], "bbox": bbox, "rk": rk,
                    "uncertain": False, "blockIdx": absorbed_idx, **style}

    # the document's largest text (its title, on the cover) never belongs
    # inside a callout; a band/frame around it is page decoration, not an
    # aside. Headline-scale text below the top rank stays eligible.
    title_size = max(top_size or 0, 1.8 * body_size)
    if page["n"] == 1 and any(_dominant_size(blocks[i]) >= 0.95 * title_size
                              for i in inside + big_inside):
        ctx.log.entry("region-skip-title", page=page["n"],
                      bbox=[round(v, 1) for v in bbox])
        return None

    uncertain = False
    # text-rich regions are callouts even when they contain an image (logo
    # sidebars); genuine figures carry at most label-scale text
    if graphic and (chars_inside <= 150 or
                    (n_images == 0 and chars_inside <= 400)):
        kind = "figure"
        # text-bearing vector region: the figure/callout call is genuinely close
        uncertain = n_images == 0 and chars_inside > 100
    elif (graphic or boxed) and (inside or big_inside):
        kind = "callout"
        uncertain = graphic and not boxed
    else:
        return None

    # big text is excluded only from figures (hero-photo titles must survive
    # the crop); a callout's oversized text is its headline and belongs inside
    absorbed_idx = inside if kind == "figure" else sorted(inside + big_inside)
    rk = ctx.log.entry(kind, page=page["n"], bbox=[round(v, 1) for v in bbox],
                       images=n_images, paths=n_paths, shadings=n_shade,
                       text_blocks=len(absorbed_idx), chars_inside=chars_inside,
                       kept_big_text=[texts[i][:40] for i in big_inside]
                                     if kind == "figure" else [],
                       reason=f"images={n_images} shadings={n_shade} paths={n_paths} "
                              f"chars_inside={chars_inside}")
    return {"kind": kind, "page": page["n"], "bbox": bbox, "rk": rk,
            "uncertain": uncertain, "blockIdx": absorbed_idx, **style}


SEG_LINETO, SEG_MOVETO = 0, 2


def _region_borders(cluster, bbox):
    """Per-side borders: stroked path segments tell us WHICH sides a box
    outline actually draws (and at what width - a full 4-side outline keeps
    its real stroke width this way); thin filled bars hugging an edge count
    too. Returns {side: [colorIdx, width_pt]}."""
    l0, b0, r0, t0 = bbox
    borders = {}
    for o in cluster["objs"]:
        if o[OT] != OBJ_PATH:
            continue
        # thin filled edge bars
        if o[7] and o[5] is not None:
            w, h = o[3] - o[1], o[4] - o[2]
            if w <= 20 and h >= 0.6 * (t0 - b0):
                side = "left" if abs(o[1] - l0) <= 6 else \
                       "right" if abs(o[3] - r0) <= 6 else None
                if side:
                    borders[side] = [o[5], round(w, 1)]
            elif h <= 20 and w >= 0.6 * (r0 - l0):
                side = "bottom" if abs(o[2] - b0) <= 6 else \
                       "top" if abs(o[4] - t0) <= 6 else None
                if side:
                    borders[side] = [o[5], round(h, 1)]
        # stroked outline with segment data; the path bbox includes the
        # stroke's overhang, so the tolerance must clear the full width
        if o[8] and len(o) > 10 and o[10] and o[6] is not None:
            sides = _seg_sides(o[10], (o[1], o[2], o[3], o[4]),
                               max(4.0, 1.5 * (o[9] or 1.0)))
            if sides:
                for side in sides:
                    borders[side] = [o[6], o[9] or 1.0]
    return borders


def _seg_sides(segs, bbox, tol):
    l0, b0, r0, t0 = bbox
    sides = set()

    def classify(p1, p2):
        (x1, y1), (x2, y2) = p1, p2
        if abs(x1 - x2) <= tol and abs(y1 - y2) > tol:
            x = (x1 + x2) / 2
            if abs(x - l0) <= tol:
                sides.add("left")
            elif abs(x - r0) <= tol:
                sides.add("right")
        elif abs(y1 - y2) <= tol and abs(x1 - x2) > tol:
            y = (y1 + y2) / 2
            if abs(y - b0) <= tol:
                sides.add("bottom")
            elif abs(y - t0) <= tol:
                sides.add("top")

    cur = start = None
    for x, y, styp, close in segs:
        if styp == SEG_MOVETO:
            cur = start = (x, y)
        else:
            if styp == SEG_LINETO and cur:
                classify(cur, (x, y))
            cur = (x, y)
        if close and cur and start:
            classify(cur, start)
    return sides


def _find_captions(ctx, regions, blocks, texts, absorbed, body_size, roles):
    for reg in regions:
        if reg["kind"] != "figure":
            continue
        for i, blk in enumerate(blocks):
            if i in absorbed or blk["page"] != reg["page"]:
                continue
            gap = reg["bbox"][1] - blk["bbox"][3]  # region bottom - block top
            if not (-2 <= gap <= 25):
                continue
            if not _h_overlap(reg["bbox"], blk["bbox"]):
                continue
            text = texts[i]
            keyword = re.match(r"(figure|fig\.|table|chart|exhibit|source[:.])",
                               text, re.I)
            tagged_caption = roles[i][0] == "Caption" and roles[i][1] > 0.5
            captionish = (keyword or tagged_caption
                          or _dominant_size(blk) < 0.95 * body_size)
            if captionish and len(text) < 500:
                reg["caption"] = text
                reg["captionIdx"] = i  # rich runs for the caption leaf
                # small font as the only signal => genuinely unsure
                reg["captionWeak"] = not (keyword or tagged_caption)
                reg["captionBlock"] = blk["rk"]
                absorbed[i] = reg
                ctx.log.entry("caption", page=reg["page"], figure=reg["rk"],
                              gap=round(gap, 1), text=text[:80])
                break
        # a labeled line directly ABOVE the figure is its title ("Figure 1:
        # ..."): the figure's header, kept inside the <figure>
        for i, blk in enumerate(blocks):
            if i in absorbed or blk["page"] != reg["page"]:
                continue
            gap = blk["bbox"][1] - reg["bbox"][3]  # block bottom - region top
            if not (-2 <= gap <= 25):
                continue
            if not _h_overlap(reg["bbox"], blk["bbox"]):
                continue
            text = texts[i]
            keyword = re.match(r"(figure|fig\.|table|chart|exhibit)\b",
                               text, re.I)
            tagged = roles[i][0] == "Caption" and roles[i][1] > 0.5
            if (keyword or tagged) and len(text) < 300:
                reg["title"] = text
                reg["titleIdx"] = i
                reg["titleBlock"] = blk["rk"]
                absorbed[i] = reg
                ctx.log.entry("figure-title", page=reg["page"],
                              figure=reg["rk"], gap=round(gap, 1),
                              text=text[:80])
                break


def _h_overlap(a, b):
    overlap = min(a[2], b[2]) - max(a[0], b[0])
    return overlap > 0.5 * min(a[2] - a[0], b[2] - b[0])


def _is_label(text):
    if not text or len(text) > 30:
        return False
    non_alpha = sum(1 for c in text if not c.isalpha())
    return non_alpha / len(text) >= 0.5


# ------------------------------------------------------------------ nodes ---

def _heading_node(ctx, blk, text, level, reason, prov, used_ids, sups=None):
    # a heading carries superscripts like any other text — a footnote reference
    # in a section title / case-study heading is common. Keep them (rebased if a
    # section number is stripped/reformatted off the front) so _attach_refs links
    # them like anywhere else. [[first-class-content]]
    orig = text
    sups = [list(sp) for sp in (sups or [])]
    num, rest = _section_number(ctx, text)
    if num:
        mode = ctx.cfg["structure"].get("sectionNumbers", "styled")
        if mode == "removed":
            text = rest
            ctx.audit_claimed[blk["page"]] += _alnum(num)
        elif mode == "inline":
            text = f"{num}. {rest}"
        else:  # styled: separate element, css decides presentation
            text = rest
        # rest is orig with the front number removed; map sups from orig-offsets
        # to the final text (front region dropped, new prefix `add` chars long)
        front, add = len(orig) - len(rest), len(text) - len(rest)
        sups = [[s - front + add, e - front + add] for s, e in sups if s >= front]
        ctx.log.entry("section-number", page=blk["page"], num=num,
                      mode=mode, text=rest[:60])
    hid = _heading_id(text, used_ids)
    rk = ctx.log.entry("heading", level=level, page=blk["page"],
                       bbox=blk["bbox"], size=prov["size"], reason=reason,
                       text=text[:120], block=blk["rk"])
    node = _leaf(ctx, "heading", {"text": text, "sups": sups}, blk["page"],
                 blk["bbox"], rk, data=prov, level=level, id=hid)
    if num and ctx.cfg["structure"].get("sectionNumbers", "styled") == "styled":
        node["sectionNum"] = num
    return node


def _promote_lead_headings(ctx, nodes, used_ids):
    """Split each paragraph flagged with a bold run-in lead (_leadHead, set by
    _block_node) into a real heading node + the paragraph remainder, rebasing
    every style run (emph/links/marks via _slice_runs; refs/breaks by hand)."""
    out = []
    for n in nodes:
        lh = n.pop("_leadHead", None) if isinstance(n, dict) else None
        if not lh or n.get("type") != "paragraph":
            out.append(n)
            continue
        e0, level, lead_prov = lh
        text = n["text"]
        blk = {"page": n["page"], "bbox": n["bbox"], "rk": n.get("rk")}
        lead_sups = [[s, e] for s, e in (n.get("sups") or []) if e <= e0]
        out.append(_heading_node(ctx, blk, text[:e0].strip(), level,
                                 "bold run-in lead", dict(lead_prov), used_ids,
                                 lead_sups))
        # paragraph remainder begins at the first non-space char past the lead
        rstart = e0
        while rstart < len(text) and text[rstart] in " \t":
            rstart += 1
        rest = _slice_runs(n, rstart, len(text))   # emph/links/marks rebased to 0
        n["text"] = rest["text"]
        for key in _RUN_KEYS:
            if rest.get(key):
                n[key] = rest[key]
            elif key in n:
                del n[key]
        if n.get("refs"):
            refs = [[s - rstart, e - rstart, v] for s, e, v in n["refs"] if s >= rstart]
            if refs:
                n["refs"] = refs
            else:
                del n["refs"]
        if n.get("breaks"):
            br = [b - rstart for b in n["breaks"] if b > rstart]
            if br:
                n["breaks"] = br
            else:
                del n["breaks"]
        n.pop("lead", None)   # the inline soft-header is now a real heading
        n["nid"] = _stable_id("n", ctx.nids, "paragraph", n["page"],
                              n["bbox"], n["text"])
        out.append(n)
    return out


def _section_number(ctx, text):
    """'4Institutional Strategies' — a design-element section number glued to
    the heading (circle/badge numerals). Only fires with no space between the
    digits and a capitalized word."""
    m = re.match(r"^(\d{1,2})(?=[A-Z][a-z])", text)
    if m:
        return m.group(1), text[m.end():].strip()
    return None, text


def _block_node(ctx, blk, rich, fonts, levels, body_size, used_ids,
                in_aside=False, role=(None, 0.0), tag_levels=None,
                kicker_level=0):
    text = rich["text"]
    size = _dominant_size(blk)
    font_votes = Counter()
    for l in blk["lines"]:
        font_votes[l["fontIdx"]] += len(l["text"])
    # char-weighted dominant, NOT the first line: a styled lead-in line
    # must not paint the whole paragraph (soft headers)
    font = fonts[font_votes.most_common(1)[0][0]]
    prov = {"font": font["name"], "weight": font["weight"], "size": size}
    color_votes = Counter()
    for l in blk["lines"]:
        color_votes[l["colorIdx"]] += len(l["text"])
    if color_votes:
        prov["color"] = _hex(ctx.colors[color_votes.most_common(1)[0][0]])
    dc = blk["lines"][0].get("dropCap")
    if dc:
        dc_w = ctx.fonts[dc[2]]["weight"] if len(dc) > 2 else 400
        prov["dropCap"] = f"{dc[0]} {_hex(ctx.colors[dc[1]])} {dc_w}"
    if not in_aside:
        bg = _block_bg(ctx, blk)
        if bg:
            prov["bg"] = bg
    tag_role, tag_cov = role
    if tag_role:
        prov["role"] = tag_role

    ov = _override_for(ctx.cfg["structure"].get("headingOverrides", []), text)
    if ov is not None and not in_aside:
        level = ov.get("level", 0)
        ctx.log.entry("heading-override", page=blk["page"], block=blk["rk"],
                      level=level, text=text[:60])
        if level:
            return _heading_node(ctx, blk, text, min(level, 6),
                                 "config headingOverride (user answer)",
                                 prov, used_ids, rich.get("sups"))
        tag_levels = None   # forced paragraph: fall through, skip heading paths
        levels = {}
        kicker_level = 0

    if not in_aside and tag_levels and tag_role in tag_levels and tag_cov > 0.5 \
            and text.strip():
        return _heading_node(ctx, blk, text, tag_levels[tag_role],
                             f"struct tag {tag_role} (coverage {tag_cov:.2f})",
                             prov, used_ids, rich.get("sups"))

    if not in_aside and size in levels \
            and _looks_like_heading(text, big=size >= 1.5 * body_size):
        level = levels[size]
        # authors tag genuine headings as P often enough that a P tag must
        # not veto strong size evidence — but the disagreement is exactly
        # what the question system is for
        conflict = bool(tag_levels) and tag_role == "P" and tag_cov > 0.5
        reason = f"size {size} ranked #{level} above body {body_size}"
        if conflict:
            reason += " (struct tag says P — kept as heading, question emitted)"
        node = _heading_node(ctx, blk, text, level, reason, prov, used_ids, rich.get("sups"))
        if conflict:
            _question(ctx, "tag-conflict-heading", node,
                      f"“{text[:60]}” looks like a heading by size, but the "
                      f"document's tags call it a paragraph. Which is right?",
                      [f"h{level}", "paragraph"], f"h{level}")
        elif size < body_size * 1.3:  # barely above body text: genuinely unsure
            _question(ctx, "heading-or-paragraph", node,
                      f"“{text[:60]}” is only slightly larger than body text. "
                      f"Heading (h{level}) or ordinary paragraph?",
                      [f"h{level}", "paragraph"], f"h{level}")
        return node

    if not in_aside and kicker_level and _is_caps_kicker(text):
        # high-precision pattern (sampled): no per-instance question, it
        # would flood the panel on label-heavy docs; feedback covers misses
        return _heading_node(ctx, blk, text, kicker_level,
                             "ALL-CAPS standalone kicker at body size",
                             prov, used_ids, rich.get("sups"))

    if not in_aside and kicker_level and len(blk["lines"]) == 1 \
            and NOTES_HEADING.fullmatch(text.strip()):
        # section labels like "Sources" deserve a heading even at body size
        return _heading_node(ctx, blk, text, kicker_level,
                             "notes-section label", prov, used_ids, rich.get("sups"))

    if _is_bullet_list(blk):
        items = _bullet_items(ctx, blk)
        rk = ctx.log.entry("list", page=blk["page"], bbox=blk["bbox"],
                           items=len(items),
                           reason="opens with a bullet; unbulleted lines are wraps",
                           block=blk["rk"])
        prov["marker"] = blk["lines"][0]["text"][:1]
        node = {"type": "list", "items": items, "page": blk["page"],
                "bbox": blk["bbox"], "rk": rk, "data": prov}
        node["nid"] = _stable_id("n", ctx.nids, "list", node["page"],
                                 node["bbox"], " ".join(_item_texts(items)))
        return node

    ol = _ordinal_block(ctx, blk)
    if ol is not None:
        style, start, items = ol
        rk = ctx.log.entry("list", page=blk["page"], bbox=blk["bbox"],
                           items=len(items), ordered=style, start=start,
                           reason="sequential ordinal markers", block=blk["rk"])
        node = {"type": "list", "items": items, "ordered": style,
                "start": start, "page": blk["page"], "bbox": blk["bbox"],
                "rk": rk, "data": prov}
        node["nid"] = _stable_id("n", ctx.nids, "list", node["page"],
                                 node["bbox"], " ".join(_item_texts(items)))
        return node

    strong = in_aside and size > 1.15 * body_size
    align = _block_align(blk, size)
    if align:
        prov["align"] = align
    refs = _extract_refs(text, rich.get("sups"))
    rk = ctx.log.entry("paragraph", page=blk["page"], bbox=blk["bbox"],
                       size=size, strong=strong, refs=[r[2] for r in refs],
                       links=len(rich.get("links", [])),
                       text=text[:120], block=blk["rk"])
    node = _leaf(ctx, "paragraph", rich, blk["page"], blk["bbox"], rk,
                 data=prov)
    if strong:
        node["strong"] = True
    if refs:
        node["refs"] = refs

    # Run-in heading: a bold first line, on its own line and heading-shaped,
    # welded onto the front of a regular-weight paragraph IS a real subsection
    # heading (the author set it bold instead of larger). Detected on the
    # glyph-width emph signal — the project's bold source of truth — so it
    # catches leads in the SAME font cut as the body, where the fontIdx-based
    # soft-header path is blind. Marked here; _promote_lead_headings splits it
    # into a heading + the paragraph remainder. Guards: the bold must cover the
    # whole first line (line-aligned, not a mid-line emphasized clause) and the
    # body below must be mostly regular weight (so a fully-bold callout/statement
    # is never carved up).
    joins = rich.get("lineJoins") or []
    emph = rich.get("emph") or []
    if not in_aside and len(blk["lines"]) >= 2 and joins:
        e0 = joins[0]
        head_txt = text[:e0].strip()
        # the bold must START the block and END right at the first-line boundary:
        # a heading occupies exactly its own line. A bold run that spills PAST e0
        # is a multi-line bold lead-in (e.g. a wrapped list-item label
        # "Improving governance, capacity, and transparency:"), not a heading.
        lead_strong = any(k == "strong" and s <= 1 and e0 - 3 <= e <= e0 + 3
                          for s, e, k in emph)
        body_len = len(text) - e0
        strong_after = sum(min(e, len(text)) - max(s, e0) for s, e, k in emph
                           if k == "strong" and min(e, len(text)) > max(s, e0))
        body_regular = body_len > 30 and strong_after <= 0.4 * body_len
        words = head_txt.split()
        # a short all-capitalized lead is a person's name (a signature/byline
        # "Pepe Zhang" over a title line), not a section heading. Real run-in
        # headings are longer or carry lowercase function words ("the", "for").
        name_like = len(words) <= 3 and all(w[:1].isupper()
                                            for w in words if w[:1].isalpha())
        # a lead ending on a dangling function word is a WRAPPED CLAUSE, not a
        # heading: a bold sentence opener ("…significant entry points for") or a
        # multi-line heading whose line 1 we'd otherwise truncate ("…seeking
        # already in the"). A real heading ends on a content word.
        last = re.sub(r"[^\w]+$", "", head_txt).rsplit(" ", 1)[-1].lower()
        dangling = last in _LEAD_STOPWORDS
        if (lead_strong and body_regular and not name_like and not dangling
                and 0 < len(head_txt) <= 90 and len(words) <= 14
                and head_txt[0] not in BULLETS and head_txt[0] not in "“\"‘'»›▶◀«‹"
                and _looks_like_heading(head_txt)):
            level = min(6, (max(levels.values()) if levels else 2) + 1)
            l0 = blk["lines"][0]
            lead_prov = {"font": fonts[l0["fontIdx"]]["name"],
                         "weight": fonts[l0["fontIdx"]]["weight"], "size": size,
                         "color": _hex(ctx.colors[l0["colorIdx"]])}
            node["_leadHead"] = [e0, level, lead_prov]
            ctx.log.entry("lead-heading", page=blk["page"], block=blk["rk"],
                          level=level, head=head_txt[:60])
            return node

    brk_ov = _override_for(ctx.cfg["structure"].get("breakOverrides", []), text)
    if brk_ov is not None:
        ctx.log.entry("break-override", page=blk["page"], block=blk["rk"],
                      breaks=brk_ov.get("breaks"), text=text[:60])
        if brk_ov.get("breaks") and rich.get("lineJoins"):
            node["breaks"] = _wrap_joins(text, rich["lineJoins"])
        return node
    lead = _soft_header(ctx, blk, rich)
    if lead:
        node["lead"] = lead
        l0 = blk["lines"][0]
        prov["leadFont"] = fonts[l0["fontIdx"]]["name"]
        prov["leadColor"] = _hex(ctx.colors[l0["colorIdx"]])
        breaks = node.get("breaks") or []
        if lead not in breaks:
            node["breaks"] = sorted([*breaks, lead])
        # the lead outranks any styled-link span inferred over it
        if node.get("links"):
            node["links"] = [l for l in node["links"]
                             if not (l[0] < lead and l[2].get("styled"))]
            if not node["links"]:
                del node["links"]
        ctx.log.entry("soft-header", page=blk["page"], block=blk["rk"],
                      lead=text[:lead][:50])
    if blk.get("pitch") and not _hard_returns(blk):
        # typed line breaks, joined by the page's line pitch; the
        # document-level typed-lines question owns presentation here.
        # Blocks with their own hard-returns evidence (short item lines:
        # 'English Phone 1%' stacks) keep the per-block path below even in
        # a typed document.
        prov["pitch"] = True
        if ctx.cfg["structure"].get("typedLines", "join") == "preserve" \
                and rich.get("lineJoins"):
            node["breaks"] = _wrap_joins(text, rich["lineJoins"])
    elif _hard_returns(blk) and rich.get("lineJoins"):
        node["breaks"] = _wrap_joins(text, rich["lineJoins"])
        _name_emphasis(node, text)
        ctx.log.entry("hard-returns", page=blk["page"], block=blk["rk"],
                      lines=len(blk["lines"]),
                      reason="2+ interior lines end with terminal punctuation")
        _question(ctx, "hard-returns", node,
                  f"“{text[:60]}…” looks like intentional one-per-line text "
                  "(credits, addresses). Keep the line breaks, or flow it as "
                  "one paragraph?",
                  ["line breaks", "flowing paragraph"], "line breaks")
    return node


GLOSSARY_RE = re.compile(r"\b(key terms|glossary|definitions)\b", re.I)


def _definition_lists(ctx, nodes):
    """A glossary section (heading matching Key Terms/Glossary/Definitions)
    whose body strictly alternates short term lines with single definition
    paragraphs becomes a real <dl> - 'lavishly semantic'. The gate is the
    section heading: ordinary kicker+paragraph structure never converts."""
    out = []
    i = 0
    while i < len(nodes):
        n = nodes[i]
        out.append(n)
        i += 1
        if n["type"] != "heading" or not GLOSSARY_RE.search(n["text"] or ""):
            continue
        # greedy term/definition pairing from the section start; the first
        # violation (a Sources label, a closing paragraph) ends the list
        j = i
        pairs = []
        while j + 1 < len(nodes):
            t, d = nodes[j], nodes[j + 1]
            text = (t.get("text") or "").strip()
            is_term = (t["type"] in ("heading", "paragraph")
                       and 0 < len(text) <= 60
                       and not NOTES_HEADING.fullmatch(text))
            if is_term and pairs:
                # terms share one style; a heading styled differently is
                # the next section, not a term - that's the list boundary
                t0 = pairs[0][0].get("data") or {}
                td = t.get("data") or {}
                is_term = all(td.get(k) == t0.get(k)
                              for k in ("font", "size", "color"))
            if not (is_term and d["type"] == "paragraph"
                    and not (d.get("text") or "").startswith("»")):
                break
            pairs.append((t, d))
            j += 2
        if len(pairs) < 3:
            continue
        children = []
        for t, d in pairs:
            t["dl"] = "dt"
            d["dl"] = "dd"
            children.extend([t, d])
        page = children[0]["page"]
        bbox = [min(c["bbox"][0] for c in children),
                min(c["bbox"][1] for c in children),
                max(c["bbox"][2] for c in children),
                max(c["bbox"][3] for c in children)]
        rk = ctx.log.entry("deflist", page=page, terms=len(pairs),
                           section=n["text"][:40])
        out.append({"type": "deflist", "children": children, "page": page,
                    "bbox": bbox, "rk": rk, "data": {},
                    "nid": _stable_id("n", ctx.nids, "deflist", page, bbox,
                                      children[0].get("text"))})
        i = j
    return out


def _marker_lists(ctx, nodes):
    """Consecutive lines led by a jump marker ('» A Note of Welcome') are a
    list, not a heading run; render upgrades them to a <nav> when the texts
    resolve to in-document headings."""
    out = []
    run = []

    def flush():
        nonlocal run
        if len(run) >= 3:
            # strip the leading '» ' marker but keep each line's style runs
            # (a jump entry can be italic/linked) instead of flattening to text
            def _cut_jump(node):
                m = re.match(r"^»\s*", node.get("text", ""))
                return _node_item(node, m.end() if m else 0)
            items = [_cut_jump(r) for r in run]
            page = run[0]["page"]
            bbox = [min(r["bbox"][0] for r in run),
                    min(r["bbox"][1] for r in run),
                    max(r["bbox"][2] for r in run),
                    max(r["bbox"][3] for r in run)]
            rk = ctx.log.entry("list", page=page, bbox=bbox,
                               items=len(items), reason="» jump markers",
                               merged=[r["rk"] for r in run])
            out.append({"type": "list", "items": items, "page": page,
                        "bbox": bbox, "rk": rk, "data": {"marker": "»"},
                        "nid": _stable_id("n", ctx.nids, "list", page, bbox,
                                          " ".join(_item_texts(items)))})
        else:
            out.extend(run)
        run = []

    for n in nodes:
        if n["type"] in ("heading", "paragraph") \
                and (n.get("text") or "").startswith("»") \
                and (not run or n["page"] == run[-1]["page"]):
            run.append(n)
        else:
            flush()
            out.append(n)
    flush()
    return out


def _merge_crosspage_lists(ctx, nodes):
    """An ordered list whose items continue past the page break: the
    continuation arrives as one fused paragraph ('b. Lecturer:X 9. Community
    ...') because the marker structure inverts mid-line. Tokens that are
    exactly the next expected sub-letter or item number are markers; every
    other digit/letter-dot token is content."""
    out = []
    for n in nodes:
        prev = out[-1] if out else None
        if (prev is not None and prev["type"] == "list"
                and prev.get("ordered") == "decimal"
                and n["type"] == "paragraph"
                and n["page"] == prev["page"] + 1):
            added = _parse_list_continuation(prev, n)
            if added:
                ctx.log.entry("list-continued", page=n["page"],
                              into=prev["rk"], segments=added,
                              text=n["text"][:60])
                ctx.audit_moved[n["page"]] += _alnum(n["text"])
                continue
        out.append(n)
    return out


def _merge_crosspage_bullet_lists(ctx, nodes):
    """An unordered list whose items continue past a page break arrives as two
    list nodes: the first ends at the FOOT of page N, the second opens at the
    HEAD of page N+1, with nothing between them (an intervening heading/lead-in
    would break the adjacency, so this can't fuse a genuinely new list).
    Concatenate the continuation's items into the first."""
    out = []
    for n in nodes:
        prev = out[-1] if out else None
        if (prev is not None and prev["type"] == "list" and n["type"] == "list"
                and not prev.get("ordered") and not n.get("ordered")
                and n["page"] == prev["page"] + 1):
            hp = ctx.page_h.get(prev["page"], 792)
            hn = ctx.page_h.get(n["page"], 792)
            if prev["bbox"][1] < 0.22 * hp and n["bbox"][3] > 0.78 * hn:
                prev["items"] = list(prev.get("items", [])) + list(n.get("items", []))
                prev["bbox"] = _union(prev["bbox"], n["bbox"])
                ctx.audit_moved[n["page"]] += sum(
                    _alnum(t) for t in _item_texts(n.get("items", [])))
                ctx.log.entry("list-continued-bullet", page=n["page"],
                              into=prev["rk"], added=len(n.get("items", [])),
                              text=next(_item_texts(n.get("items", [])), "")[:50])
                continue
        out.append(n)
    return out


def _parse_list_continuation(lst, node):
    items = lst["items"]
    if not items or not isinstance(items[-1], dict):
        return 0
    text = node.get("text", "")
    sub = items[-1].get("sub") or {}
    sub_style = sub.get("ordered", "lower-alpha")
    expect_num = lst.get("start", 1) + len(items)
    expect_sub = sub.get("start", 1) + len(sub.get("items", []))
    tok = re.compile(r"(?:^|(?<=\s))(\d{1,2}|[a-z])[.)]\s*")
    accepted = []
    for m in tok.finditer(text):
        raw = m.group(1)
        if raw.isdigit():
            if int(raw) != expect_num:
                continue
            accepted.append(("item", m))
            expect_num += 1
            expect_sub = 1
        else:
            if ord(raw) - 96 != expect_sub:
                continue
            accepted.append(("sub", m))
            expect_sub += 1
    if len(accepted) < 2 or text[:accepted[0][1].start()].strip():
        return 0
    for (kind, m), nxt in zip(accepted, accepted[1:] + [None]):
        end = nxt[1].start() if nxt else len(text)
        # slice the continuation paragraph's own style runs into the item so a
        # bold/linked fragment that wrapped past the page break survives
        content = _cut_item(_slice_runs(node, m.end(), end), 0)
        if kind == "item":
            items.append(content)
        else:
            s = items[-1].setdefault(
                "sub", {"ordered": sub_style, "start": 1, "items": []})
            s["items"].append(content)
    return len(accepted)


def _name_emphasis(node, text):
    """Credits blocks alternate names with '(affiliation)' lines; the names
    deserve <strong> even when the PDF styles them identically - semantic
    structure the source only implied (≥2 paren lines required)."""
    breaks = node.get("breaks") or []
    bounds = [0, *breaks, len(text)]
    segs = [(bounds[k] + (1 if k else 0), bounds[k + 1])
            for k in range(len(bounds) - 1)]
    paren = [k for k, (s, e) in enumerate(segs)
             if text[s:e].lstrip()[:1] == "("]
    if len(paren) < 2:
        return
    emph = node.setdefault("emph", [])
    for k in paren:
        if k == 0 or (k - 1) in paren:
            continue
        s, e = segs[k - 1]
        emph.append([s, e, "strong"])
    emph.sort()


def _soft_header(ctx, blk, rich):
    """Run-in 'soft header': the block's first line, entirely in a style the
    rest of the block doesn't share (blue italic 'Gender'), short, no
    terminal punctuation. Too local to be a real heading - it renders as
    <b class="soft-header"> with a line break after it, original styling
    restored by layer 3. Returns the lead's end offset or None."""
    lines = blk["lines"]
    joins = rich.get("lineJoins") or []
    if len(lines) < 2 or not joins:
        return None
    l0 = lines[0]
    t0 = l0["text"].strip()
    if not (0 < len(t0) <= 45) or t0[-1:] in ".!?:;,":
        return None
    if t0[0] in BULLETS or t0[0] in "“\"‘'":
        return None  # bullet items and opening quotes are not labels
    rest_fonts = {l["fontIdx"] for l in lines[1:]}
    rest_colors = {l["colorIdx"] for l in lines[1:]}
    if l0["fontIdx"] in rest_fonts and l0["colorIdx"] in rest_colors:
        return None
    if len(rest_fonts) > 2:
        return None  # mixed body: no confidence in "distinct" lead
    e = joins[0]
    # a lead with a REAL link annotation is a link; the styled-link
    # inference (link-colored text without a target) loses to the
    # soft-header shape - blue labels are labels
    if any(s < e and not t.get("styled")
           for s, _e, t in rich.get("links", [])):
        return None
    return e


def _wrap_joins(text, joins):
    """Hard-return blocks reproduce the PDF's line breaks - except inside an
    unclosed parenthesis, where the break wraps one long item ('(Executive
    Office of the Secretary | General, United Nations)'), not a new line."""
    return [j for j in joins
            if text[:j].count("(") <= text[:j].count(")")]


def _hard_returns(blk):
    """Intentional one-per-line blocks. Two tells:
    - sentence-per-line (credits): 2+ interior lines end in terminal
      punctuation — wrapped prose almost never does;
    - contact-card form: interior lines fall well short of the block edge
      AND successive lines start new items (capital/digit/paren) without the
      previous line ending a sentence."""
    lines = blk["lines"]
    if len(lines) < 3:
        return False
    interior = lines[:-1]
    terminal = sum(1 for l in interior if l["text"].rstrip()[-1:] in ".!?:")
    if terminal >= 2 and terminal >= 0.6 * len(interior):
        return True

    left = min(l["bbox"][0] for l in lines)
    width = max(max(l["bbox"][2] for l in lines) - left, 1.0)
    short = sum(1 for l in interior if l["bbox"][2] < left + 0.75 * width)
    item_starts = sum(
        1 for prev, nxt in zip(lines, lines[1:])
        if prev["text"].rstrip()[-1:] not in ".,;:-"
        and (nxt["text"][:1].isupper() or nxt["text"][:1].isdigit()
             or nxt["text"][:1] == "("))
    if short >= 2 and item_starts >= 2 and item_starts >= 0.6 * len(interior):
        return True
    # one interior line ending FAR short (under 60% width) never happens in
    # wrapped prose - enough on its own when transitions look like items
    # (contact cards whose longest line is the interior address)
    short60 = sum(1 for l in interior if l["bbox"][2] < left + 0.6 * width)
    if short60 >= 1 and item_starts >= 0.6 * (len(lines) - 1):
        return True
    # a uniform stack of short item lines ('English Phone 1%' label-value
    # stats): wrapped prose lines run long, so equal-width short lines with
    # every transition starting an item are a stack, not a wrap
    return (len(lines) >= 3 and item_starts == len(lines) - 1
            and all(len(l["text"]) <= 45 for l in lines))


def _block_bg(ctx, blk):
    """The colored panel a main-flow block sits ON: the last-drawn (topmost)
    non-white filled rect that covers the block and is meaningfully larger than
    it. This is the styling the region classifier deliberately skipped (cover
    panels around the document title, section banner bands) — the text stays in
    the flow, but its background is real appearance (rubric north star) and
    also the context that makes light text colors legible. Page-wide fills
    (>70% of the page) are excluded — a tinted page ground is a future
    body-background feature, not a per-block panel."""
    bl, bb, br, bt = blk["bbox"]
    barea = max((br - bl) * (bt - bb), 1.0)
    pw, ph = ctx.page_dims.get(blk["page"], (612.0, 792.0))
    best = None
    for o in ctx.page_objs.get(blk["page"], []):
        if o[0] != OBJ_PATH or not o[7] or o[5] is None:
            continue
        l, b, r, t = o[1:5]
        farea = (r - l) * (t - b)
        if farea < 1.4 * barea or farea > 0.7 * pw * ph:
            continue
        ix = min(br, r) - max(bl, l)
        iy = min(bt, t) - max(bb, b)
        if ix <= 0 or iy <= 0 or (ix * iy) / barea < 0.85:
            continue
        rgba = ctx.colors[o[5]]
        if rgba[3] < 128 or min(rgba[:3]) > 240:
            continue  # transparent or white-ish: not a visible panel
        best = _hex(rgba)  # objects arrive in draw order; last cover wins
    return best


def _block_align(blk, size):
    """'right'/'center' when the block's line edges say so: aligned right
    edges over a ragged left mean right-aligned, agreeing midpoints over
    ragged edges mean centered. Justified text agrees on the left too, so
    it never matches. Single lines carry no evidence."""
    lines = blk["lines"]
    if len(lines) < 2:
        return None
    ls = [l["bbox"][0] for l in lines]
    rs = [l["bbox"][2] for l in lines]
    l_spread = max(ls) - min(ls)
    r_spread = max(rs) - min(rs)
    if r_spread < 0.3 * size and l_spread > 1.5 * size:
        return "right"
    mids = [(a + b) / 2 for a, b in zip(ls, rs)]
    if (max(mids) - min(mids) < 0.3 * size
            and l_spread > 1.5 * size and r_spread > 1.5 * size):
        return "center"
    return None


def _figure_node(ctx, reg, pages, fig_count, blocks, rich):
    page = pages[reg["page"]]
    src, w_px, h_px = _crop(ctx, reg, page, fig_count)
    caption = reg.get("caption")
    title = reg.get("title")
    rk = ctx.log.entry("figure-crop", page=reg["page"], src=src,
                       bbox=[round(v, 1) for v in reg["bbox"]],
                       region=reg["rk"], caption=(caption or "")[:80],
                       title=(title or "")[:80])
    node = {"type": "figure", "src": src,
            "width": round(reg["bbox"][2] - reg["bbox"][0]),
            "height": round(reg["bbox"][3] - reg["bbox"][1]),
            "alt": title or caption or f"Figure from page {reg['page']}",
            "page": reg["page"], "bbox": reg["bbox"], "rk": rk,
            "data": {"region": reg["rk"]}}
    node["nid"] = _stable_id("n", ctx.nids, "figure", node["page"], node["bbox"])
    # unified container model: title/caption are caption containers holding a
    # paragraph leaf built from the source block's rich runs — a superscript
    # reference or a link in a caption survives like anywhere else
    kids = []
    for variant, key in (("title", "titleIdx"), ("caption", "captionIdx")):
        bi = reg.get(key)
        if bi is None:
            continue
        bbox = blocks[bi]["bbox"]
        leaf = _leaf(ctx, "paragraph", rich[bi], reg["page"], bbox, rk)
        kids.append(_container(ctx, "caption", [leaf], reg["page"], bbox, rk,
                               variant=variant))
    if kids:
        node["children"] = kids
    return node


def _crop(ctx, reg, page, fig_count):
    img = Image.open(ctx.outdir / "pages" / f"page-{reg['page']:04d}.png")
    scale = img.width / page["width"]
    l, b, r, t = reg["bbox"]
    pad = 4
    box = (max(0, int(l * scale) - pad),
           max(0, int((page["height"] - t) * scale) - pad),
           min(img.width, int(r * scale) + pad),
           min(img.height, int((page["height"] - b) * scale) + pad))
    (ctx.outdir / "images").mkdir(exist_ok=True)
    name = f"images/fig-{fig_count:03d}.png"
    crop = img.crop(box)
    crop.save(ctx.outdir / name)
    return name, crop.width, crop.height


def _color_segments(line):
    """Partition a line into its color runs: [[s, e, colorIdx]], merged and
    stripped of boundary spaces; None when the line is single-colored."""
    runs = line.get("colors") or []
    if not runs:
        return None
    text = line["text"]
    segs = []
    pos = 0
    for s, e, ci in sorted(runs):
        if s > pos:
            segs.append([pos, s, line["colorIdx"]])
        segs.append([s, e, ci])
        pos = max(pos, e)
    if pos < len(text):
        segs.append([pos, len(text), line["colorIdx"]])
    merged = []
    for s, e, ci in segs:
        while s < e and text[s] == " ":
            s += 1
        while e > s and text[e - 1] == " ":
            e -= 1
        if s >= e:
            continue
        if merged and merged[-1][2] == ci:
            merged[-1][1] = e
        else:
            merged.append([s, e, ci])
    return merged if len(merged) > 1 else None


def _try_table(ctx, reg, blocks, rich, pages, strict=False):
    """A boxed region whose grid is literally drawn (ruled lines or cell
    fills) and whose blocks cluster into columns is a table, not a callout.

    Column boundaries come from the drawn verticals and fill edges; a block
    spanning several columns is split into cells at its color-run boundaries
    (label/value panels print the label white-on-fill and the value dark).
    Cell/row/column fills, text colors and rule colors are captured as the
    table's style so layer 3 can recreate the original look.

    strict mode (regions classified as figures): also require ≥3 rows and a
    mostly-filled cell lattice, so charts with gridlines and sparse axis
    labels never convert."""
    idx = reg["blockIdx"]
    if len(idx) < 4 or reg.get("endPage"):
        return None
    page = pages[reg["page"]]
    l0, b0, r0, t0 = reg["bbox"]
    hl = vl = 0
    vxs = []
    fills = []
    border_votes = Counter()
    for o in page.get("objects", []):
        if o[0] != OBJ_PATH:
            continue
        l, b, r, t = o[1:5]
        if l < l0 - 5 or r > r0 + 5 or b < b0 - 5 or t > t0 + 5:
            continue
        if t - b < 3 and r - l > 30:
            hl += 1
            if o[8] and o[6] is not None:
                border_votes[o[6]] += 1
        elif r - l < 3 and t - b > 10:
            vl += 1
            vxs.append((l + r) / 2)
            if o[8] and o[6] is not None:
                border_votes[o[6]] += 1
        elif o[7] and o[5] is not None and r - l > 10 and t - b > 8:
            fills.append((l, b, r, t, o[5]))
    if hl < 3 or vl < 2:
        return None

    # column ranges between internal boundaries (verticals + fill edges)
    cand = sorted(vxs + [x for f in fills for x in (f[0], f[2])])
    clusters = []
    for x in cand:
        if x < l0 + 8 or x > r0 - 8:
            continue
        if clusters and x - clusters[-1][-1] < 6:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    edges = [l0, *(sum(c) / len(c) for c in clusters), r0]
    cols = list(zip(edges, edges[1:]))
    if len(cols) < 2:
        # no internal boundaries drawn: columns from block center clusters
        centers = sorted((blocks[i]["bbox"][0] + blocks[i]["bbox"][2]) / 2
                         for i in idx)
        edges = [l0]
        for a, b in zip(centers, centers[1:]):
            if b - a > 50:
                edges.append((a + b) / 2)
        edges.append(r0)
        cols = list(zip(edges, edges[1:]))
    n_cols = len(cols)
    if n_cols < 2:
        return None

    # cells: (col, top, bottom, runs, colorIdx); blocks spanning several
    # columns split at color-run boundaries, joined per column across lines.
    # Cell content stays a runs-dict (text + inline runs) end to end, so
    # bold/links/superscript references inside cells reach the leaf nodes
    # instead of collapsing to bare strings [[first-class-content]].
    cells = []
    for i in idx:
        blk = blocks[i]
        bl, bb, br, bt = blk["bbox"]
        span = [c for c, (xl, xr) in enumerate(cols)
                if min(br, xr) - max(bl, xl) > 4]
        dom = Counter()
        for line in blk["lines"]:
            dom[line["colorIdx"]] += len(line["text"])
        if len(span) <= 1:
            c = span[0] if span else min(
                range(n_cols), key=lambda c: abs((cols[c][0] + cols[c][1]) / 2
                                                 - (bl + br) / 2))
            cells.append([c, bt, bb, rich[i], dom.most_common(1)[0][0]])
            continue
        blk_font = _block_font(ctx, blk["lines"])
        parts = {}    # col -> runs-dict
        pcolor = {}   # col -> colorIdx of the column's first segment
        ok = True
        for line in blk["lines"]:
            segs = _color_segments(line)
            if not segs or len(segs) != len(span):
                ok = False
                break
            lruns = _build_runs(ctx, blk, [line], blk_font)
            for c, (s, e, ci) in zip(span, segs):
                parts[c] = _cat_runs(parts.get(c), _slice_strip(lruns, s, e))
                pcolor.setdefault(c, ci)
        if ok:
            for c in sorted(parts):
                if parts[c] and parts[c]["text"]:
                    cells.append([c, bt, bb, parts[c], pcolor[c]])
        else:
            cells.append([span[0], bt, bb, rich[i],
                          dom.most_common(1)[0][0]])

    # rows by vertical-interval grouping (top-down)
    rows_cells = []
    for cell in sorted(cells, key=lambda c: -c[1]):
        if rows_cells and cell[1] > rows_cells[-1]["min_b"]:
            rows_cells[-1]["cells"].append(cell)
            rows_cells[-1]["min_b"] = min(rows_cells[-1]["min_b"], cell[2])
        else:
            rows_cells.append({"cells": [cell], "min_b": cell[2],
                               "max_t": cell[1]})

    rows_runs = []
    row_colors = []
    for row in rows_cells:
        runs_r = [None] * n_cols
        colors_r = [None] * n_cols
        for c, _t, _b, runs, ci in row["cells"]:
            runs_r[c] = _cat_runs(runs_r[c], runs)
            colors_r[c] = ci
        rows_runs.append(runs_r)
        row_colors.append(colors_r)
    # plain-text view of the grid (header/lattice heuristics + nid input)
    rows = [[(r["text"] if r else "") for r in rr] for rr in rows_runs]
    if len(rows) < 2:
        return None
    if strict:
        filled = sum(1 for r in rows for c in r if c.strip())
        if len(rows) < 3 or filled < 0.6 * len(rows) * n_cols:
            return None

    # style: header band fill, per-column fills and text colors, rule color
    style = {}
    r0_top, r0_bot = rows_cells[0]["max_t"], rows_cells[0]["min_b"]
    head_fill = next(
        (f for f in fills
         if f[2] - f[0] > 0.7 * (r0 - l0) and f[1] <= r0_bot and f[3] >= r0_top
         and f[3] - f[1] < 0.5 * (t0 - b0)), None)
    body_fg = Counter(ci for rc in row_colors[1:] for ci in rc
                      if ci is not None)
    header = all(c.strip() for c in rows[0]) and (
        head_fill is not None
        or (body_fg and set(filter(None, row_colors[0]))
            and not set(filter(None, row_colors[0])) & set(body_fg)))
    if head_fill:
        style["headBg"] = _hex(ctx.colors[head_fill[4]])
        head_fg = Counter(ci for ci in row_colors[0] if ci is not None)
        if head_fg:
            style["headFg"] = _hex(ctx.colors[head_fg.most_common(1)[0][0]])
    body_top = r0_bot if header else t0
    col_bg = []
    col_fg = []
    for c, (xl, xr) in enumerate(cols):
        bg = next((f for f in fills
                   if min(f[2], xr) - max(f[0], xl) > 0.6 * (xr - xl)
                   and f[2] - f[0] < 1.5 * (xr - xl)
                   and min(f[3], body_top) - max(f[1], b0)
                   > 0.5 * (body_top - b0)), None)
        col_bg.append(_hex(ctx.colors[bg[4]]) if bg else None)
        fg = Counter(rc[c] for rc in row_colors[1 if header else 0:]
                     if rc[c] is not None)
        col_fg.append(_hex(ctx.colors[fg.most_common(1)[0][0]]) if fg else None)
    if any(col_bg):
        style["colBg"] = col_bg
    if any(col_fg):
        style["colFg"] = col_fg
    border = next((ci for ci, _ in border_votes.most_common()
                   if _hex(ctx.colors[ci]) != "#ffffff"), None)
    if border is not None:
        style["border"] = _hex(ctx.colors[border])

    rk = ctx.log.entry("table", page=reg["page"], bbox=[round(v, 1) for v in reg["bbox"]],
                       cols=n_cols, rows=len(rows), header=header,
                       hlines=hl, vlines=vl, region=reg["rk"], style=style,
                       strict=strict)
    # unified container model: table > row > cell > paragraph leaf. The leaf
    # carries the cell's inline runs, so _attach_refs / ops / audit reach cell
    # content through the same generic children walk as everything else.
    row_nodes = []
    for rr, rc in zip(rows_runs, rows_cells):
        cell_nodes = []
        for c, (xl, xr) in enumerate(cols):
            cb = [xl, rc["min_b"], xr, rc["max_t"]]
            kids = []
            if rr[c] and rr[c]["text"]:
                kids.append(_leaf(ctx, "paragraph", rr[c], reg["page"], cb, rk))
            cell_nodes.append(_container(ctx, "cell", kids, reg["page"], cb, rk))
        row_nodes.append(_container(ctx, "row", cell_nodes, reg["page"],
                                    [l0, rc["min_b"], r0, rc["max_t"]], rk))
    node = {"type": "table", "children": row_nodes, "header": header,
            "page": reg["page"], "bbox": reg["bbox"], "rk": rk,
            "data": {"region": reg["rk"]}}
    if style:
        node["style"] = style
    node["nid"] = _stable_id("n", ctx.nids, "table", reg["page"], reg["bbox"],
                             " ".join(rows[0]))
    return node


def _aside_images(ctx, reg, node, pages, fig_count):
    """Images inside a callout region become figure children (the logo /
    photo lives in the box, not lost to it)."""
    page = pages[reg["page"]]
    repeated = _repeated_images(pages)
    figs = []
    for o in page.get("objects", []):
        if o[0] != OBJ_IMAGE or _okey(page["n"], o) in repeated:
            continue
        cx, cy = (o[1] + o[3]) / 2, (o[2] + o[4]) / 2
        if not (reg["bbox"][0] <= cx <= reg["bbox"][2]
                and reg["bbox"][1] <= cy <= reg["bbox"][3]):
            continue
        if (o[3] - o[1]) * (o[4] - o[2]) < 400:
            continue  # icons
        fig_count += 1
        sub = {"page": page["n"], "bbox": [o[1], o[2], o[3], o[4]]}
        src, w_px, h_px = _crop(ctx, sub, page, fig_count)
        rk = ctx.log.entry("aside-image", page=page["n"], src=src,
                           bbox=sub["bbox"], region=reg["rk"])
        figs.append({"type": "figure", "src": src,
                     "width": round(o[3] - o[1]),
                     "height": round(o[4] - o[2]),
                     "alt": f"Image from page {page['n']}",
                     "page": page["n"], "bbox": sub["bbox"], "rk": rk,
                     "data": {"region": reg["rk"]},
                     "nid": _stable_id("n", ctx.nids, "figure", page["n"],
                                       sub["bbox"])})
    if figs:
        node["children"] = sorted(
            node["children"] + figs,
            key=lambda c: (c["page"], -c["bbox"][3]))
    return fig_count


def _aside_node(ctx, reg, blocks, rich, fonts, body_size, roles):
    # callout boxes are single-column: order children top-down by position
    # (page first, for boxes merged across a page break) so the headline
    # leads regardless of content-stream order
    ordered = sorted(reg["blockIdx"],
                     key=lambda i: (blocks[i]["page"], -blocks[i]["bbox"][3]))
    children = [_block_node(ctx, blocks[i], rich[i], fonts, {}, body_size,
                            set(), in_aside=True, role=roles[i])
                for i in ordered]
    children = _group_tag_lists(ctx, children)
    children = _group_bullet_paragraphs(ctx, children)
    children = _join_pagebreak_sentences(ctx, children)
    is_quote = _extract_quote_marks(ctx, reg, children)
    if len(children) == 1:
        # a lone child is the box's content, not a headline over content
        children[0].pop("strong", None)
    rk = ctx.log.entry("aside", page=reg["page"],
                       bbox=[round(v, 1) for v in reg["bbox"]],
                       end_page=reg.get("endPage"),
                       region=reg["rk"], children=len(children))
    node = {"type": "aside", "children": children, "page": reg["page"],
            "bbox": reg["bbox"], "rk": rk, "data": {"region": reg["rk"]}}
    if reg.get("fillIdx") is not None:
        node["data"]["fill"] = _hex(ctx.colors[reg["fillIdx"]])
    if reg.get("strokeIdx") is not None:
        node["data"]["stroke"] = _hex(ctx.colors[reg["strokeIdx"]])
    if reg.get("borders"):
        node["borders"] = {side: {"color": _hex(ctx.colors[ci]), "width": w}
                           for side, (ci, w) in reg["borders"].items()}
    if is_quote:
        node["quote"] = True
    first_text = next((c.get("text") for c in children if c.get("text")), None)
    node["nid"] = _stable_id("n", ctx.nids, "aside", node["page"], node["bbox"],
                             first_text)
    return node


# -------------------------------------------------------------- text utils ---

def _side_rows(ctx, items, blocks, body_size, page_n):
    """Side-by-side card groups. Blocks in disjoint x-ranges whose tops align
    and that share a style distinct from the page's prose are parallel
    siblings (a card row), not column flow: grouping them into one full-width
    "row" item keeps the pair together through column banding, and render
    emits the cells as a grid. Style match is the discriminator - two-column
    prose paragraphs routinely share tops, but they carry the page's dominant
    style and never seed a row."""
    def sig(item):
        kind, ref = item
        if kind != "block":
            return None
        ln = blocks[ref]["lines"][0]
        return (ln.get("fontIdx"), round(ln.get("size", 0.0)),
                ln.get("colorIdx"))

    def bbox(item):
        kind, ref = item
        return blocks[ref]["bbox"] if kind == "block" else ref["bbox"]

    sigs = [sig(it) for it in items]
    counts = Counter(s for s in sigs if s is not None)
    body_sig = counts.most_common(1)[0][0] if counts else None
    boxes = [bbox(it) for it in items]

    # seed pairs: aligned tops, x-disjoint, same non-prose style
    groups = []  # [member indexes, y_lo, y_hi]
    for a in range(len(items)):
        if sigs[a] is None or sigs[a] == body_sig:
            continue
        for b in range(a + 1, len(items)):
            if sigs[b] != sigs[a]:
                continue
            A, B = boxes[a], boxes[b]
            if abs(A[3] - B[3]) > 2.0:
                continue
            if not (A[2] + 6 <= B[0] or B[2] + 6 <= A[0]):
                continue
            groups.append([{a, b}, min(A[1], B[1]), max(A[3], B[3])])
    if not groups:
        return None

    # one card = a stack of seed pairs (title pair above body pair): merge
    # groups that overlap vertically or sit a line apart with nothing
    # foreign between them
    groups.sort(key=lambda g: -g[2])
    merged = [groups[0]]
    for g in groups[1:]:
        prev = merged[-1]
        if g[0] & prev[0] or g[2] >= prev[1]:
            overlap = True
        elif prev[1] - g[2] <= 1.5 * body_size:
            # a separator (e.g. a heading) lies wholly in the gap; an item
            # that overlaps either group is row content, not a separator
            overlap = not any(
                i not in prev[0] and i not in g[0]
                and boxes[i][3] > g[2] and boxes[i][1] < prev[1]
                and boxes[i][1] >= g[2] and boxes[i][3] <= prev[1]
                for i in range(len(items)))
        else:
            overlap = False
        if overlap:
            prev[0] |= g[0]
            prev[1] = min(prev[1], g[1])
            prev[2] = max(prev[2], g[2])
        else:
            merged.append(g)

    rows = []
    for members, y_lo, y_hi in merged:
        if len(members) < 4:  # at least two seed pairs make a card row
            continue
        # cells from seed x-intervals (overlap-transitive clusters)
        ivals = sorted((boxes[i][0], boxes[i][2]) for i in members)
        cells_x = [list(ivals[0])]
        for lo, hi in ivals[1:]:
            if lo <= cells_x[-1][1]:
                cells_x[-1][1] = max(cells_x[-1][1], hi)
            else:
                cells_x.append([lo, hi])
        if len(cells_x) < 2:
            continue
        # absorb the rest of the row's vertical span (icon figures etc.),
        # assigned to the overlapping or nearest cell
        cells = [[] for _ in cells_x]
        for i in range(len(items)):
            box = boxes[i]
            if i not in members and not (box[1] < y_hi and box[3] > y_lo):
                continue
            ci = min(range(len(cells_x)),
                     key=lambda c: max(cells_x[c][0] - box[2],
                                       box[0] - cells_x[c][1], 0))
            cells[ci].append(i)
        for cell in cells:
            cell.sort(key=lambda i: -boxes[i][3])
        used = [i for cell in cells for i in cell]
        union = [min(boxes[i][0] for i in used),
                 min(boxes[i][1] for i in used),
                 max(boxes[i][2] for i in used),
                 max(boxes[i][3] for i in used)]
        rk = ctx.log.entry("side-row", page=page_n, bbox=union,
                           cells=[len(c) for c in cells],
                           members=[_item_rk(items[i], blocks) for i in used])
        rows.append((set(used), {
            "cells": [[items[i] for i in cell] for cell in cells],
            "bbox": union, "rk": rk}))
    if not rows:
        return None

    out = []
    placed = set()
    taken = {i for used, _ in rows for i in used}
    for i, it in enumerate(items):
        if i not in taken:
            out.append(it)
            continue
        for ri, (used, row) in enumerate(rows):
            if i in used and ri not in placed:
                placed.add(ri)
                out.append(("row", row))
    return out


def _heading_aside_rows(ctx, items, blocks, body_size, page_n):
    """Heading-left / body-right rows (asymmetric, unlike _side_rows' matched
    cards). A heading-styled block in a left column, with body content to its
    right and nothing below it in its OWN column, governs that right content as a
    band ("Leverage loan…" heading + its bullet list to the right). Left alone,
    the column-first XY-cut reads every left heading and THEN every right body
    ("h1 h2 b1 b2"); grouping each heading with its band restores "h1 b1 h2 b2".
    Distinguished from a per-column header (which reads column-major) by the body
    — not another heading — sitting to the heading's right; and the "nothing below
    it in its own column" gate rules out a heading that merely tops a 2-col flow."""
    def sig(it):
        kind, ref = it
        if kind != "block":
            return None
        ln = blocks[ref]["lines"][0]
        return (ln.get("fontIdx"), round(ln.get("size", 0.0)), ln.get("colorIdx"))

    def bbox(it):
        kind, ref = it
        return blocks[ref]["bbox"] if kind == "block" else ref["bbox"]

    sigs = [sig(it) for it in items]
    counts = Counter(s for s in sigs if s is not None)
    if not counts:
        return None
    body_sig = counts.most_common(1)[0][0]
    boxes = [bbox(it) for it in items]
    is_body = lambda i: sigs[i] == body_sig

    headings = []
    for h in range(len(items)):
        if sigs[h] is None or sigs[h] == body_sig:
            continue
        # a sidebar heading is visually LARGER than body — guards against dense
        # infographics where scattered small chart labels (7-9pt) would each
        # qualify as a "heading" with body coincidentally to their right
        if sigs[h][1] < body_size + 1:
            continue
        H = boxes[h]
        # body to the right, sharing the heading's vertical band
        has_right = any(i != h and is_body(i) and boxes[i][0] >= H[2] + 6
                        and boxes[i][1] < H[3] and boxes[i][3] > H[1]
                        for i in range(len(items)))
        if not has_right:
            continue
        # ...and NOTHING of substance below it in its own column (else it's a
        # heading topping a normal two-column flow → leave to column-major)
        below_left = any(i != h and is_body(i) and boxes[i][3] <= H[1] + 1
                         and boxes[i][0] < H[2] and boxes[i][2] > H[0]
                         for i in range(len(items)))
        if not below_left:
            headings.append(h)
    if len(headings) < 2:  # a repeated pattern, not a one-off
        return None
    if max(boxes[h][0] for h in headings) > min(boxes[h][2] for h in headings):
        return None  # the headings must stack in one shared left column

    headings.sort(key=lambda h: -boxes[h][3])  # top-down
    tops = [boxes[h][3] for h in headings]
    gutter = min(boxes[h][2] for h in headings)  # right edge of the heading column
    bands, used_all = {}, set()
    for k, h in enumerate(headings):
        top = tops[k]
        nxt = tops[k + 1] if k + 1 < len(headings) else float("-inf")
        band = [i for i in range(len(items))
                if i != h and i not in used_all and boxes[i][0] >= gutter + 6
                and nxt < (boxes[i][1] + boxes[i][3]) / 2 <= top]
        if not band:
            continue
        band.sort(key=lambda i: -boxes[i][3])
        used_all.update(band)
        used_all.add(h)
        bands[h] = band
    if len(bands) < 2:
        return None

    # Emit a FLAT reading order, not a grid: each heading expands to itself then
    # its right-column band; loose items keep their place. Flat (vs grid cells)
    # so the downstream list/figure grouping still sees the band's bullets as
    # siblings and merges them into one list. Units sort top-down by their head.
    units = [(boxes[h][3], [h] + band) for h, band in bands.items()]
    units += [(boxes[i][3], [i]) for i in range(len(items)) if i not in used_all]
    units.sort(key=lambda u: -u[0])
    ctx.log.entry("heading-aside", page=page_n, rows=len(bands),
                  order=[blocks[items[i][1]]["lines"][0]["text"][:24]
                         if items[i][0] == "block" else "·"
                         for _, seq in units for i in seq])
    return [items[i] for _, seq in units for i in seq]


def _item_rk(item, blocks):
    kind, ref = item
    return blocks[ref].get("rk") if kind == "block" else ref.get("rk")


def _interior_gaps(intervals):
    """Empty spans BETWEEN the merged coverage of 1-D intervals — i.e. gaps with
    content on both sides (page margins excluded). Returns [(lo, hi), …]."""
    es = sorted(intervals)
    merged = [list(es[0])]
    for lo, hi in es[1:]:
        if lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    return [(merged[i][1], merged[i + 1][0]) for i in range(len(merged) - 1)]


# A vertical valley narrower than this isn't a column gutter; a horizontal one
# narrower than this isn't a band break (paragraph leading stays inside a block).
MIN_GUTTER = 8.0
MIN_BAND = 11.0


def _tag_verdict(ro_src):
    """Document tagging verdict from the per-page reading-order source counts:
    'full' (most multi-item pages use the declared struct-tree order), 'partial'
    (some), or 'none' (no usable object-level tags — geometry everywhere)."""
    struct, geom = ro_src.get("struct-tree", 0), ro_src.get("geometry", 0)
    total = struct + geom
    if not struct:
        return {"verdict": "none", "structPages": 0, "totalPages": total}
    verdict = "full" if struct >= 0.8 * total else "partial"
    return {"verdict": verdict, "structPages": struct, "totalPages": total}


def _struct_order(tagged, bbox):
    """The declared reading-order index for `bbox`: the struct-tree sequence of
    the tagged region it overlaps most (artifacts/untagged regions carry -1 and
    are ignored). -1 when nothing tagged covers it. See _struct_roles."""
    bl, bb, br, bt = bbox
    best, best_area = -1, 0.0
    for reg in tagged:
        if len(reg) < 6:
            continue
        l, b, r, t, _role, seq = reg[:6]
        if seq is None or seq < 0:
            continue
        ix = min(br, r) - max(bl, l)
        iy = min(bt, t) - max(bb, b)
        if ix > 0 and iy > 0 and ix * iy > best_area:
            best_area, best = ix * iy, seq
    return best


def _reading_order_topo(bboxes):
    """Breuel/OCRopus reading order by topological sort over before-after
    constraints (docs/research/reading-order.md). For each ordered pair:
      - x-overlap (same column) and A higher → A before B (read down a column);
      - no x-overlap and A fully left of B, with NO third block between them →
        A before B (read left column before right). The "between" guard stops a
        wrong cross-column edge when an intervening block mediates the order.
    A full-width header x-overlaps both columns, so the higher-element rule puts
    it first with no special-casing. Topological-sort the DAG, breaking ties (and
    any cycle from a genuinely ambiguous layout) by reading position. No
    recursive cut and no global whitespace threshold — the XY-cut failure modes
    (spanning headers, split sentences, column order) don't apply."""
    n = len(bboxes)
    if n <= 1:
        return list(range(n))

    def xov(u, v):
        return bboxes[u][0] < bboxes[v][2] and bboxes[u][2] > bboxes[v][0]

    def higher(u, v):           # u's top above v's top (PDF y grows upward)
        return bboxes[u][3] > bboxes[v][3]

    def left_of(u, v):          # u entirely left of v
        return bboxes[u][2] <= bboxes[v][0]

    def between(w, u, v):       # w in the horizontal gap u|v, sharing their band
        ww = bboxes[w]
        ytop = max(bboxes[u][3], bboxes[v][3])
        ybot = min(bboxes[u][1], bboxes[v][1])
        if ww[1] >= ytop or ww[3] <= ybot:   # w outside their vertical span
            return False
        return ww[0] < bboxes[u][2] and ww[2] > bboxes[v][0]

    succ = [[] for _ in range(n)]
    indeg = [0] * n

    def add(i, j):
        succ[i].append(j)
        indeg[j] += 1

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if xov(i, j):
                if higher(i, j):
                    add(i, j)
            elif left_of(i, j) and not any(
                    between(w, i, j) for w in range(n) if w != i and w != j):
                add(i, j)

    pos = lambda k: (-bboxes[k][3], bboxes[k][0])  # higher first, then leftmost
    seen = [False] * n
    ready = [k for k in range(n) if indeg[k] == 0]
    out = []
    while len(out) < n:
        if ready:
            ready.sort(key=pos)
            k = ready.pop(0)
        else:                    # cycle (ambiguous layout): best remaining
            k = min((x for x in range(n) if not seen[x]), key=pos)
        if seen[k]:
            continue
        seen[k] = True
        out.append(k)
        for j in succ[k]:
            indeg[j] -= 1
            if indeg[j] == 0 and not seen[j]:
                ready.append(j)
    return out


def _reading_order(bboxes):
    """Recursive XY-cut reading order over block bboxes — replaces bespoke
    column detection + left-then-right flow. Recursively split the region at its
    widest whitespace valley: a VERTICAL valley separates columns (left read
    first), a HORIZONTAL valley separates bands (top read first). Crucially a
    vertical valley only exists when NO block spans it, so a full-width header
    forces a horizontal cut first (its own band), then the columns below split —
    which is exactly correct reading order. Handles any column count, banded
    headers, and nested layouts uniformly. Returns (index_order, max_columns)."""
    max_cols = [1]

    def recurse(idxs, cols_here):
        if len(idxs) <= 1:
            max_cols[0] = max(max_cols[0], cols_here)
            return list(idxs)
        bs = [bboxes[i] for i in idxs]
        region_w = max(b[2] for b in bs) - min(b[0] for b in bs)
        vgaps = _interior_gaps([(b[0], b[2]) for b in bs])  # x → column gutters
        hgaps = _interior_gaps([(b[1], b[3]) for b in bs])  # y → band breaks
        bv = max(vgaps, key=lambda g: g[1] - g[0], default=None)
        bh = max(hgaps, key=lambda g: g[1] - g[0], default=None)
        vw = (bv[1] - bv[0]) if bv else 0.0
        hw = (bh[1] - bh[0]) if bh else 0.0
        v_ok, h_ok = vw >= MIN_GUTTER, hw >= MIN_BAND
        # COLUMNS FIRST: a valid gutter is cut before any horizontal band, so
        # continuous columns (a per-column heading then its body) read down each
        # column rather than across the heading row. A full-width banded header
        # has no vertical gutter (it spans), so it still falls to the horizontal
        # cut below — banded layouts are unaffected.
        if v_ok:
            x = (bv[0] + bv[1]) / 2
            left = [i for i in idxs if (bboxes[i][0] + bboxes[i][2]) / 2 < x]
            right = [i for i in idxs if i not in left]
            # real columns COEXIST vertically; if the two sides barely overlap in
            # y they're stacked blocks that merely happen to be x-disjoint, not a
            # gutter — guards against over-segmentation (a short line's right
            # margin reading as a column). Require the shorter side to overlap.
            lb, rb = [bboxes[i] for i in left], [bboxes[i] for i in right]
            yov = (min(max(b[3] for b in lb), max(b[3] for b in rb))
                   - max(min(b[1] for b in lb), min(b[1] for b in rb)))
            short_h = min(max(b[3] for b in lb) - min(b[1] for b in lb),
                          max(b[3] for b in rb) - min(b[1] for b in rb))
            if yov >= 0.5 * max(short_h, 1.0):
                return (recurse(left, cols_here + 1)
                        + recurse(right, cols_here + 1))
        if h_ok:
            y = (bh[0] + bh[1]) / 2
            top = [i for i in idxs if (bboxes[i][1] + bboxes[i][3]) / 2 > y]
            bot = [i for i in idxs if i not in top]
            return recurse(top, cols_here) + recurse(bot, cols_here)
        # whitespace-cover assist: when a full-width block straddles the gutter
        # AND overlaps the columns (no clean band gap above it), pure XY-cut
        # deadlocks. Treat the block as a band boundary on its own — split the
        # region above/below it — so the columns on each side can then cut.
        spanning = [i for i in idxs
                    if (bboxes[i][2] - bboxes[i][0]) >= 0.7 * max(region_w, 1.0)]
        if spanning and len(spanning) < len(idxs):
            s = max(spanning, key=lambda i: (bboxes[i][1] + bboxes[i][3]) / 2)
            sy = (bboxes[s][1] + bboxes[s][3]) / 2
            above = [i for i in idxs
                     if i != s and (bboxes[i][1] + bboxes[i][3]) / 2 > sy]
            below = [i for i in idxs if i != s and i not in above]
            return recurse(above, cols_here) + [s] + recurse(below, cols_here)
        # no cut available: read top-to-bottom, then left-to-right
        max_cols[0] = max(max_cols[0], cols_here)
        return sorted(idxs, key=lambda i: (-bboxes[i][3], bboxes[i][0]))

    return recurse(list(range(len(bboxes))), 1), max_cols[0]


def _group_tag_lists(ctx, nodes):
    """Struct tags declare lists (L > LI > Lbl/LBody) even when the bullet
    glyphs defeat char-based detection. Consecutive LBody/LI paragraphs become
    one list node; tiny Lbl marker nodes are dropped."""
    out = []
    run = []
    last_lbl = [None]

    def flush():
        nonlocal run
        if len(run) >= 2:
            # each LBody/LI paragraph carries its own emphasis/link runs; keep
            # them so a bold lead-in sentence or inline link survives the merge
            items = [_strip_marker_item(_node_runs(n), BULLETS) for n in run]
            bbox = [min(n["bbox"][0] for n in run), min(n["bbox"][1] for n in run),
                    max(n["bbox"][2] for n in run), max(n["bbox"][3] for n in run)]
            page = run[0]["page"]
            # numbered tagged lists arrive with "1. / 2. / 3." baked into the
            # item text — act on that here and emit a real <ol> (markers stripped,
            # rendered by the list), not a <ul> with the numbers fossilized in.
            ol = _ordinal_items_rich(items)
            ordered = start = None
            if ol:
                ordered, start, items = ol
            rk = ctx.log.entry("list", page=page, bbox=bbox, items=len(items),
                               ordered=ordered, start=start,
                               reason="struct tags LBody/LI"
                                      + (" (ordinal)" if ordered else ""),
                               merged=[n["rk"] for n in run])
            for n in run:
                if n["page"] != page:  # grouped across pages: credit source
                    ctx.audit_moved[n["page"]] += _alnum(n["text"])
            data = {"role": "L"}
            if last_lbl[0]:
                data["marker"] = last_lbl[0]
            node = {"type": "list", "items": items, "page": page,
                    "bbox": bbox, "rk": rk, "data": data,
                    "nid": _stable_id("n", ctx.nids, "list", page, bbox,
                                      " ".join(_item_texts(items)))}
            if ordered:
                node["ordered"], node["start"] = ordered, start
            out.append(node)
        else:
            out.extend(run)
        run = []

    for n in nodes:
        role = (n.get("data") or {}).get("role")
        if n["type"] == "paragraph" and role == "Lbl" \
                and len(n.get("text", "")) <= 3:
            last_lbl[0] = n.get("text", "").strip() or last_lbl[0]
            ctx.log.entry("drop-lbl", page=n["page"], text=n.get("text", ""))
            ctx.audit_claimed[n["page"]] += _alnum(n.get("text"))
            continue
        if n["type"] == "paragraph" and role in ("LBody", "LI"):
            run.append(n)
        else:
            flush()
            out.append(n)
    flush()
    return out


def _split_inline_bullets(ctx, nodes):
    """A list that got mashed into one paragraph — 'lead-in: • item • item • item'
    — where the bullet glyphs survive INSIDE the text. There's almost never a
    real bullet sitting mid-sentence, so interior bullets mark list items.
    Split into the lead-in paragraph (kept) + an unordered list, preserving each
    piece's emphasis/links. Skips bullet-as-separator rows (short labels, no
    sentence punctuation: datelines, contact lines)."""
    out = []
    for n in nodes:
        t = n.get("text", "") if n.get("type") == "paragraph" else ""
        # interior bullets: a TRUE bullet glyph (not a hyphen/dash) with real
        # text before it
        pts = [i for i, c in enumerate(t) if c in INLINE_BULLETS and t[:i].strip()]
        if len(pts) < 2:               # need >=2 to read as a list, not a stray glyph
            out.append(n)
            continue
        bounds = pts + [len(t)]
        raw = [re.sub(f"^[{re.escape(INLINE_BULLETS)}]\\s*", "", t[bounds[k]:bounds[k + 1]]).strip()
               for k in range(len(pts))]
        # separator guard: a row of short labels joined by bullets isn't a list
        if all(len(s.split()) <= 5 for s in raw) and not any(s[-1:] in ".!?" for s in raw):
            out.append(n)
            continue
        items = [_strip_marker_item(_slice_runs(n, bounds[k], bounds[k + 1]), INLINE_BULLETS)
                 for k in range(len(pts))]
        lead = t[:pts[0]].strip()
        if lead:
            lr = _slice_runs(n, 0, pts[0])
            n["text"] = lr["text"].rstrip()
            for key in ("emph", "links", "marks", "colors"):
                if lr.get(key):
                    n[key] = lr[key]
                elif key in n:
                    del n[key]
            out.append(n)
        ctx.log.entry("list-from-inline-bullets", page=n["page"], block=n.get("rk"),
                      items=len(items), lead=lead[:50])
        out.append({"type": "list", "items": items, "page": n["page"],
                    "bbox": n["bbox"], "rk": n.get("rk"),
                    "data": {**(n.get("data") or {}), "marker": t[pts[0]]},
                    "nid": _stable_id("n", ctx.nids, "list", n["page"], n["bbox"],
                                      " ".join(_item_texts(items)))})
    return out


def _group_bullet_paragraphs(ctx, nodes):
    """List items that arrived as separate blocks group into one list:
    bullet-led paragraphs, or sequential ordinal-led paragraphs (numbered /
    lettered), with deeper-indented alpha runs nesting under the preceding
    numeric item."""
    nodes = _group_ordinal_paragraphs(ctx, nodes)
    out = []
    run = []

    def flush():
        nonlocal run
        if not run:
            return
        # each bullet paragraph already carries its own style runs over its text;
        # preserve them as the item's spans (bullet stripped, rebased)
        items = [_strip_marker_item(_node_runs(n), BULLETS) for n in run]
        bbox = [min(n["bbox"][0] for n in run), min(n["bbox"][1] for n in run),
                max(n["bbox"][2] for n in run), max(n["bbox"][3] for n in run)]
        page = run[0]["page"]
        # A bullet run (even a single item) sitting right after an unordered
        # list at the same indent is that list's tail items that split into
        # their own block — rejoin them rather than orphaning a one-bullet <p>.
        prev = out[-1] if out else None
        if (prev is not None and prev["type"] == "list" and not prev.get("ordered")
                and prev["page"] == page and abs(prev["bbox"][0] - bbox[0]) <= 6):
            prev["items"] = list(prev.get("items", [])) + items
            prev["bbox"] = _union(prev["bbox"], bbox)
            ctx.log.entry("list-item-rejoined", page=page, into=prev["rk"],
                          added=len(items),
                          text=next(_item_texts(items), "")[:50])
            run = []
            return
        if len(run) >= 2:
            rk = ctx.log.entry("list", page=page, bbox=bbox, items=len(items),
                               reason="consecutive bullet-led paragraphs",
                               merged=[n["rk"] for n in run])
            for n in run:
                if n["page"] != page:  # grouped across pages: credit source
                    ctx.audit_moved[n["page"]] += _alnum(n["text"])
            data = dict(run[0].get("data", {}))
            data["marker"] = run[0]["text"][:1]
            out.append({"type": "list", "items": items, "page": page,
                        "bbox": bbox, "rk": rk, "data": data,
                        "nid": _stable_id("n", ctx.nids, "list", page, bbox,
                                          " ".join(_item_texts(items)))})
        else:
            out.extend(run)
        run = []

    for n in nodes:
        if n["type"] == "paragraph" and n.get("text", "")[:1] in BULLETS:
            run.append(n)
        else:
            flush()
            out.append(n)
    flush()
    return out


def _group_ordinal_paragraphs(ctx, nodes):
    """Consecutive paragraphs led by sequential ordinals become one ordered
    list; an immediately following deeper-indented alpha run nests under the
    last numeric item."""
    out = []
    i = 0
    while i < len(nodes):
        n = nodes[i]
        m = _ol_marker(n.get("text", "")) if n["type"] == "paragraph" else None
        if not m:
            out.append(n)
            i += 1
            continue
        style0, start, _ = m
        run = []
        expected = start
        j = i
        base_x = n["bbox"][0]
        while j < len(nodes):
            cand = nodes[j]
            cm = _ol_marker(cand.get("text", "")) \
                if cand["type"] == "paragraph" else None
            if cm and cm[0] == style0 and cm[1] == expected:
                run.append({"item": _node_item(cand, cm[2]), "node": cand})
                expected += 1
                j += 1
                # absorb an immediately following deeper-indent alpha run
                sub_expected = None
                while j < len(nodes):
                    s = nodes[j]
                    sm = _ol_marker(s.get("text", "")) \
                        if s["type"] == "paragraph" else None
                    if sm and sm[0] != style0 and s["bbox"][0] > base_x + 6 \
                            and (sub_expected is None or sm[1] == sub_expected):
                        sub = run[-1].setdefault(
                            "sub", {"ordered": sm[0], "start": sm[1], "items": []})
                        sub["items"].append(_node_item(s, sm[2]))
                        sub_expected = sm[1] + 1
                        j += 1
                    else:
                        break
            else:
                break
        if len(run) >= 2 or (run and run[0].get("sub")):
            members = [r["node"] for r in run]
            page = members[0]["page"]
            bbox = [min(x["bbox"][0] for x in members),
                    min(x["bbox"][1] for x in members),
                    max(x["bbox"][2] for x in members),
                    max(x["bbox"][3] for x in members)]
            for x in members:
                if x["page"] != page:
                    ctx.audit_moved[x["page"]] += _alnum(x["text"])
            items = []
            for r in run:
                it = r["item"]  # always a rich dict (from _node_item)
                if r.get("sub"):
                    it["sub"] = r["sub"]
                items.append(it)
            rk = ctx.log.entry("list", page=page, bbox=bbox, items=len(items),
                               ordered=style0, start=start,
                               reason="sequential ordinal paragraphs",
                               merged=[x["rk"] for x in members])
            out.append({"type": "list", "items": items, "ordered": style0,
                        "start": start, "page": page, "bbox": bbox, "rk": rk,
                        "data": dict(members[0].get("data", {})),
                        "nid": _stable_id("n", ctx.nids, "list", page, bbox,
                                          " ".join(_item_texts(items)))})
            i = j
        else:
            out.append(n)
            i += 1
    return out


def _extract_quote_marks(ctx, reg, children):
    """Quotation glyphs leading/trailing a callout become separate elements
    so CSS can style or hide them (decorative pull-quote marks)."""
    QUOTES = "“”‘’\"'„‟"
    first = next((c for c in children if c.get("text")), None)
    last = next((c for c in reversed(children) if c.get("text")), None)
    found = False
    if first:
        m = re.match(rf"^([{QUOTES}]{{1,2}})\s*", first["text"])
        if m:
            first["quoteOpen"] = m.group(1)
            first["text"] = first["text"][m.end():]
            found = True
    if last:
        m = re.search(rf"\s*([{QUOTES}]{{1,2}})$", last["text"])
        if m:
            last["quoteClose"] = m.group(1)
            last["text"] = last["text"][:m.start()]
            found = True
    if found:
        ctx.log.entry("quote-callout", page=reg["page"], region=reg["rk"])
    return found


def _floating_pullquotes(ctx, nodes, body_size):
    """A distinctly styled paragraph sitting in the margin beside the text
    column - plus the attribution line under it - is a floating pull-quote:
    an unboxed aside, floated like the original. (The boxed/duplicated kind
    is handled in _aside_layout_and_pullquotes; this text is NOT duplicated,
    so it stays visible to screen readers.)"""
    paras = [n for n in nodes if n["type"] == "paragraph"]
    if len(paras) < 4:
        return nodes
    col_l = Counter(round(n["bbox"][0]) for n in paras).most_common(1)[0][0]
    col_paras = [n for n in paras if abs(round(n["bbox"][0]) - col_l) <= 2]
    if len(col_paras) < 3:
        return nodes
    # the column's right edge is page-local: the quote hangs past the text
    # on ITS page, not past the widest paragraph in the document
    col_r_page = {}
    for n in col_paras:
        col_r_page[n["page"]] = max(col_r_page.get(n["page"], 0),
                                    n["bbox"][2])

    quotes = {}  # id(quote node) -> [quote, attribution...]
    claimed = set()
    for p in paras:
        col_r = col_r_page.get(p["page"])
        if col_r is None or p["bbox"][0] <= col_r or id(p) in claimed:
            continue
        d = p.get("data") or {}
        distinct = (d.get("size", body_size) >= 1.2 * body_size
                    or QUOTE_CHARS & set(p.get("text", "")[:2]))
        beside = any(c["page"] == p["page"]
                     and min(c["bbox"][3], p["bbox"][3])
                     - max(c["bbox"][1], p["bbox"][1]) > 20
                     for c in col_paras)
        if not (distinct and beside and len(p.get("text", "")) >= 60):
            continue
        group = [p]
        claimed.add(id(p))
        for a in paras:
            if id(a) in claimed or a["page"] != p["page"]:
                continue
            if a["bbox"][0] >= p["bbox"][0] - 20 \
                    and a["bbox"][3] < p["bbox"][1] \
                    and p["bbox"][1] - a["bbox"][3] < 6 * body_size \
                    and a.get("text", "")[:1] in "-–—":
                group.append(a)
                claimed.add(id(a))
        quotes[id(p)] = group

    if not quotes:
        return nodes
    out = []
    for n in nodes:
        if id(n) in claimed and id(n) not in quotes:
            continue
        group = quotes.get(id(n))
        if group is None:
            out.append(n)
            continue
        bbox = [min(c["bbox"][0] for c in group),
                min(c["bbox"][1] for c in group),
                max(c["bbox"][2] for c in group),
                max(c["bbox"][3] for c in group)]
        rk = ctx.log.entry("pull-quote-floating", page=n["page"], bbox=bbox,
                           children=[c["nid"] for c in group],
                           text=n["text"][:60])
        out.append({"type": "aside", "children": group, "page": n["page"],
                    "bbox": bbox, "rk": rk, "data": {}, "pullQuote": True,
                    "nid": _stable_id("n", ctx.nids, "aside", n["page"], bbox,
                                      n["text"])})
    return out


QUOTE_CHARS = set("“\"‘'")


def _aside_layout_and_pullquotes(ctx, nodes, twocol_pages=()):
    """Two post-passes over the assembled flow:
    - asides (and, on single-column pages, figures) narrower than the text
      column get layout provenance (width fraction + anchored side) so
      layer 3 can float them like the original; two-column pages keep
      figures inline - their position is column flow, not a float;
    - an aside whose text duplicates part of a nearby paragraph is a
      pull-quote: decoration, not content (config structure.pullQuotes:
      keep => floated + aria-hidden, drop => removed)."""
    mains = [n for n in nodes if n["type"] in ("paragraph", "heading")]
    if not mains:
        return nodes
    col_l = min(n["bbox"][0] for n in mains)
    col_r = max(n["bbox"][2] for n in mains)
    col_w = max(col_r - col_l, 1.0)

    def norm(t):
        return re.sub(r"[^a-z0-9]+", "", (t or "").lower())

    para_norms = [(n, norm(n.get("text"))) for n in nodes
                  if n["type"] == "paragraph"]
    mode = ctx.cfg["structure"].get("pullQuotes", "keep")
    out = []
    for n in nodes:
        if n["type"] not in ("aside", "figure") or \
                (n["type"] == "figure" and n["page"] in twocol_pages):
            out.append(n)
            continue
        w = n["bbox"][2] - n["bbox"][0]
        frac = w / col_w
        # float thresholds (rubric §1, user's Q2a numbers): a sidebar floats on
        # its original side only at 20–50% of the column; wider ones read as
        # bands, not floats, and fall back to inline placement before the
        # related text (their natural document-order position). Org-adjustable
        # settings later.
        if 0.2 <= frac <= 0.5:
            anchor = None
            if col_r - n["bbox"][2] < 0.08 * col_w and \
                    n["bbox"][0] - col_l > 0.2 * col_w:
                anchor = "right"
            elif n["bbox"][0] - col_l < 0.08 * col_w and \
                    col_r - n["bbox"][2] > 0.2 * col_w:
                anchor = "left"
            if anchor and n["type"] == "figure":
                # a float is real only when text actually runs beside it;
                # banners, logos and stacked charts stay inline
                h = n["bbox"][3] - n["bbox"][1]
                beside = any(
                    m["page"] == n["page"]
                    and min(m["bbox"][3], n["bbox"][3])
                    - max(m["bbox"][1], n["bbox"][1]) > 0.5 * h
                    for m in mains)
                if not beside:
                    anchor = None
            if anchor:
                n["layout"] = {"widthFrac": round(frac, 3), "anchor": anchor}
                ctx.log.entry("aside-layout", page=n["page"], nid=n["nid"],
                              kind=n["type"], anchor=anchor,
                              widthFrac=n["layout"]["widthFrac"])
        if n["type"] == "figure":
            out.append(n)
            continue

        texts = [c.get("text", "") for c in n.get("children", [])]
        total = norm(" ".join(texts))
        if len(n.get("children", [])) <= 2 and 30 <= len(total) <= 400:
            dup = next((p for p, pn in para_norms
                        if total in pn and abs(p["page"] - n["page"]) <= 1), None)
            if dup is not None:
                rk = ctx.log.entry("pull-quote", page=n["page"], nid=n["nid"],
                                   duplicates=dup["nid"], mode=mode,
                                   text=texts[0][:60] if texts else "")
                if mode == "drop":
                    for c in n.get("children", []):
                        ctx.audit_claimed[c["page"]] += _alnum(c.get("text")) \
                            + sum(_alnum(i) for i in c.get("items", []))
                    continue
                n["pullQuote"] = True
                n["data"]["duplicates"] = dup["nid"]
        out.append(n)
    return out


def _join_pagebreak_sentences(ctx, children):
    """A sentence interrupted by a page break (previous paragraph ends without
    terminal punctuation, next starts lowercase on a later page) is one
    paragraph."""
    out = []
    for ch in children:
        prev = out[-1] if out else None
        if (prev is not None and prev["type"] == "paragraph"
                and ch["type"] == "paragraph" and ch["page"] > prev["page"]
                and prev.get("text") and ch.get("text")
                and prev["text"][-1] not in ".!?:;”’\""
                and ch["text"][:1].islower()):
            off = len(prev["text"]) + 1
            # joined text renders under prev's page; credit the source page
            ctx.audit_moved[ch["page"]] += _alnum(ch["text"])
            prev["text"] += " " + ch["text"]
            for key in ("refs", "links", "emph", "marks", "colors"):
                if ch.get(key):
                    prev.setdefault(key, []).extend(
                        [r[0] + off, r[1] + off, *r[2:]] for r in ch[key])
            ctx.log.entry("join-pagebreak", page=ch["page"], into=prev["rk"],
                          joined=ch["text"][:60])
            continue
        out.append(ch)
    return out


def _join_column_wrap(ctx, nodes):
    """A body paragraph that wraps from the foot of one column to the head of
    the next (same page) is split in two by block grouping. Rejoin when the
    previous ends mid-sentence and the next is the physically-higher, rightward
    next column — the geometric signature of a column break. On a single column
    the continuation sits BELOW the previous block, so this never fires."""
    out = []
    for ch in nodes:
        prev = out[-1] if out else None
        if not (prev is not None and prev["type"] == "paragraph"
                and ch["type"] == "paragraph"
                and ch["page"] == prev["page"]
                and prev.get("text") and ch.get("text")
                and not prev.get("breaks") and not ch.get("breaks")):
            out.append(ch)
            continue
        last = prev["text"].rstrip()[-1:]
        mid_sentence = last.isalnum() or last in ",-–­"
        ps = (prev.get("data") or {}).get("size", 0)
        cs = (ch.get("data") or {}).get("size", 0)
        next_column = (ch["bbox"][3] > prev["bbox"][3] + 2 and
                       (ch["bbox"][0] + ch["bbox"][2]) / 2
                       > (prev["bbox"][0] + prev["bbox"][2]) / 2 + 2)
        if not (mid_sentence and ch["text"][:1].isalpha() and next_column
                and abs(ps - cs) < 0.6):
            out.append(ch)
            continue
        ptext = prev["text"].rstrip()
        if ptext[-1:] in "-­":  # mid-word hyphen break across the column
            joiner = ""
            prev["text"] = ptext[:-1]
        else:
            joiner = " "
        off = len(prev["text"]) + len(joiner)
        ctx.audit_moved[ch["page"]] += _alnum(ch["text"])
        prev["text"] += joiner + ch["text"]
        for key in ("refs", "links", "emph", "marks", "colors"):
            if ch.get(key):
                prev.setdefault(key, []).extend(
                    [r[0] + off, r[1] + off, *r[2:]] for r in ch[key])
        ctx.log.entry("join-column-wrap", page=ch["page"], into=prev["rk"],
                      joined=ch["text"][:60])
    return out


def _join_broken_paragraphs(ctx, nodes):
    """The broken-paragraph signature — the first block ends mid-sentence and the
    next starts lowercase — split by block grouping within a page. Rejoins both
    a same-column vertical split (second directly below the first) AND a side-by-
    side column wrap the geometry-strict _join_column_wrap misses (columns level
    at the top, so the continuation isn't 'higher'). Page breaks: see
    _join_pagebreak_sentences. The lowercase start is the high-precision guard."""
    out = []
    for ch in nodes:
        prev = out[-1] if out else None
        # ch must not be a structured (hard-return) block; prev may carry breaks
        # only when they're a run-in soft-header (lead) at its start, which says
        # nothing about joining its END to a continuation
        if not (prev is not None and prev["type"] == "paragraph"
                and ch["type"] == "paragraph" and ch["page"] == prev["page"]
                and prev.get("text") and ch.get("text")
                and (prev.get("lead") or not prev.get("breaks"))
                and not ch.get("breaks")):
            out.append(ch)
            continue
        last = prev["text"].rstrip()[-1:]
        mid_sentence = last.isalnum() or last in ",-–­"
        ps = (prev.get("data") or {}).get("size", 0)
        cs = (ch.get("data") or {}).get("size", 0)
        pcx, ccx = (prev["bbox"][0] + prev["bbox"][2]) / 2, (ch["bbox"][0] + ch["bbox"][2]) / 2
        # (a) same column, ch directly below prev within ~2 lines
        same_col = (abs(ch["bbox"][0] - prev["bbox"][0]) < 8
                    and ch["bbox"][3] <= prev["bbox"][1] + 2
                    and prev["bbox"][1] - ch["bbox"][3] < max(ps, cs, 1) * 2.5)
        # (b) next column: ch is rightward and vertically overlaps prev (not
        # entirely below it) — the column-boundary wrap
        next_col = ccx > pcx + 2 and ch["bbox"][3] > prev["bbox"][1]
        if not (mid_sentence and ch["text"][:1].islower() and (same_col or next_col)
                and abs(ps - cs) < 0.6):
            out.append(ch)
            continue
        ptext = prev["text"].rstrip()
        if ptext[-1:] in "-­":            # mid-word hyphen break
            joiner = ""
            prev["text"] = ptext[:-1]
        else:
            joiner = " "
        off = len(prev["text"]) + len(joiner)
        ctx.audit_moved[ch["page"]] += _alnum(ch["text"])
        prev["text"] += joiner + ch["text"]
        for key in ("refs", "links", "emph", "marks", "colors"):
            if ch.get(key):
                prev.setdefault(key, []).extend(
                    [r[0] + off, r[1] + off, *r[2:]] for r in ch[key])
        prev["bbox"] = _union(prev["bbox"], ch["bbox"])
        ctx.log.entry("join-broken-para", page=ch["page"], into=prev["rk"],
                      joined=ch["text"][:60])
    return out


def _dominant_size(blk):
    sizes = Counter()
    for l in blk["lines"]:
        sizes[l["size"]] += len(l["text"])
    return sizes.most_common(1)[0][0]


def _body_size(ctx, blocks):
    """Body text size = most common size weighted by char count."""
    sizes = Counter()
    for blk in blocks:
        for l in blk["lines"]:
            sizes[round(l["size"], 1)] += len(l["text"])
    body = sizes.most_common(1)[0][0] if sizes else 10.0
    ctx.log.entry("body-size", size=body, distribution=dict(sizes.most_common(8)))
    return body


def _heading_levels(ctx, blocks, texts, body_size):
    """Distinct sizes clearly above body size, ranked desc -> h1, h2, ...
    Only blocks whose text plausibly *is* a heading participate in the
    ranking, so oversized pull-quotes don't steal the h1 slot."""
    cand = sorted({_dominant_size(b) for b, t in zip(blocks, texts)
                   if _dominant_size(b) > body_size * 1.15 and _looks_like_heading(t)},
                  reverse=True)
    levels = {size: min(i + 1, 6) for i, size in enumerate(cand)}
    ctx.log.entry("heading-levels", body_size=body_size,
                  mapping={str(s): lv for s, lv in levels.items()})
    return levels


def _is_caps_kicker(text):
    """Standalone ALL-CAPS line(s) at body size: small-caps style headers."""
    text = text.strip()
    if not (8 <= len(text) <= 90) or text.endswith((".", ",", ";")):
        return False
    if len(text.split()) < 2:
        return False
    letters = [c for c in text if c.isalpha()]
    return len(letters) >= 8 and all(c.isupper() for c in letters)


def _looks_like_heading(text, big=False):
    text = text.strip()
    if re.fullmatch(r"[\$€£]?[\d,.\s]+%?", text):
        return False  # numeric/currency labels are not headings
    # a trailing colon reads as a lead-in, not a heading - unless the text
    # is display-sized ("Inclusive, local hiring:" at 3x body)
    enders = (".", ",", ";", "…") if big else (".", ",", ";", ":", "…")
    return (0 < len(text) <= 200
            and not text.endswith(enders)
            and re.search(r"[A-Za-z0-9]{2}", text) is not None)


def _is_bullet_list(blk):
    """Bullet items wrap: the block is a list when it opens with a bullet and
    has at least two bulleted lines; unbulleted lines are continuations."""
    starts = [l["text"][:1] in BULLETS for l in blk["lines"]]
    return len(starts) >= 2 and starts[0] and sum(starts) >= 2


def _item_texts(items):
    for it in items:
        if isinstance(it, str):       # tolerate any not-yet-migrated path
            yield it
            continue
        yield it.get("text", "")
        sub = it.get("sub")
        if sub:
            for s in sub.get("items", []):
                yield s if isinstance(s, str) else s.get("text", "")


def _ordinal_block(ctx, blk):
    """A block whose lines carry sequential ordinal markers (any start, for
    resumed numbering: <ol start>). Deeper-indented alpha lines under a numeric
    item nest one level. Items keep their emphasis/links (a bold lead-in
    survives). Returns (style, start, items) or None."""
    lines = blk["lines"]
    first = _ol_marker(lines[0]["text"])
    if first is None or len(lines) < 2:
        return None
    style0, start, off0 = first
    base_x = lines[0]["bbox"][0]
    # group lines per item, tracking each item's marker offset and any sub-list.
    # A sub-list collects its own line-GROUPS (not raw strings) so each sub-item
    # is built through _build_runs and keeps its emphasis/links/marks too.
    groups = [{"lines": [lines[0]], "off": off0, "sub": None}]
    expected, marked = start + 1, 1
    for l in lines[1:]:
        m = _ol_marker(l["text"])
        if m and m[0] == style0 and m[1] == expected:
            groups.append({"lines": [l], "off": m[2], "sub": None})
            expected += 1
            marked += 1
        elif m and m[0] != style0 and l["bbox"][0] > base_x + 6:
            sub = groups[-1]["sub"]
            if sub is None:
                sub = groups[-1]["sub"] = {"ordered": m[0], "start": m[1],
                                           "groups": []}
            sub["groups"].append({"lines": [l], "off": m[2]})
            marked += 1
        elif groups[-1]["sub"] and groups[-1]["sub"]["groups"]:
            groups[-1]["sub"]["groups"][-1]["lines"].append(l)
        else:
            groups[-1]["lines"].append(l)
    if marked < 2:
        return None
    blk_font = _block_font(ctx, lines)
    items = []
    for g in groups:
        item = _cut_item(_build_runs(ctx, blk, g["lines"], blk_font), g["off"])
        if g["sub"]:
            sg = g["sub"]
            item["sub"] = {"ordered": sg["ordered"], "start": sg["start"],
                           "items": [_cut_item(_build_runs(ctx, blk, s["lines"],
                                                            blk_font), s["off"])
                                     for s in sg["groups"]]}
        items.append(item)
    return style0, start, items


# the style runs a text unit carries: each is a [start, end, payload?] span list
# over its own text. `sups` (superscript ranges) rides along like the rest so a
# list item / table cell keeps the signal a paragraph would — references live in
# ALL text, not just paragraphs ([[first-class-content]]); _attach_refs turns
# sups into refs everywhere and then drops the raw sups.
_RUN_KEYS = ("emph", "links", "marks", "colors", "sups")


def _node_runs(node):
    """A node's text plus its full rich payload (emphasis/links/marks) as a
    runs-dict — the single shape every list-item builder slices from, so no
    construction path has to re-derive (and thus drop) style from raw text."""
    return {"text": node.get("text", ""),
            **{k: node.get(k) for k in _RUN_KEYS}}


def _cut_item(runs, cut):
    """Drop the first `cut` chars (a leading marker) plus any following spaces
    from a runs-dict and rebase its style offsets. ALWAYS returns a rich item
    dict {"text", "emph"?, "links"?, "marks"?} — never a bare string — so every
    list item can carry style and a dropped run becomes structurally impossible
    (see _assert_rich_items)."""
    full = runs.get("text", "")
    while cut < len(full) and full[cut] == " ":
        cut += 1
    text = full[cut:].rstrip()
    n = len(text)

    def rebase(spans):
        out = []
        for sp in spans or []:
            s, e = max(sp[0] - cut, 0), min(sp[1] - cut, n)
            if e > s:
                out.append([s, e, *sp[2:]])
        return out

    item = {"text": text}
    for key in _RUN_KEYS:
        reb = rebase(runs.get(key))
        if reb:
            item[key] = reb
    return item


def _strip_marker_item(runs, markers):
    """Drop a leading marker glyph (bullet) from a runs-dict, preserving the
    style runs (rebased)."""
    m = re.match(f"^[{re.escape(markers)}]\\s*", runs.get("text", ""))
    return _cut_item(runs, m.end() if m else 0)


def _node_item(node, cut):
    """Build a list item from a paragraph node, keeping its style runs."""
    return _cut_item(_node_runs(node), cut)


def _as_runs(item):
    """A rich list item as a runs dict."""
    return {"text": item.get("text", ""),
            **{k: item.get(k) for k in _RUN_KEYS}}


def _ordinal_items_rich(items):
    """Like _ordinal_items but PRESERVES each item's emphasis/links: detect a
    consecutive ordinal sequence (1.2.3 / a.b.c) from the item texts, strip the
    markers, and rebase the runs. Returns (style, start, stripped_items) or None.
    Used so a numbered tagged list keeps its bold lead-ins."""
    texts = list(_item_texts(items))
    if len(texts) < 2:
        return None
    first = _ol_marker(texts[0])
    if first is None:
        return None
    style, start, off = first
    stripped = [_cut_item(_as_runs(items[0]), off)]
    expected, marked = start + 1, 1
    for it, t in zip(items[1:], texts[1:]):
        m = _ol_marker(t)
        if m and m[0] == style and m[1] == expected:
            stripped.append(_cut_item(_as_runs(it), m[2]))
            expected += 1
            marked += 1
        else:
            stripped.append(_cut_item(_as_runs(it), 0))  # wrapped / unmarked
    if marked < 2 or marked < 0.6 * len(texts):
        return None
    return style, start, stripped


def _slice_runs(node, a, b):
    """A runs-dict for the sub-range [a,b) of a node's text, with all style
    offsets (emphasis/links/marks) clipped and rebased to 0."""
    def reb(spans):
        out = []
        for sp in spans or []:
            s, e = max(sp[0], a), min(sp[1], b)
            if e > s:
                out.append([s - a, e - a, *sp[2:]])
        return out
    return {"text": node.get("text", "")[a:b],
            **{k: reb(node.get(k)) for k in _RUN_KEYS}}


def _upgrade_lists(ctx, nodes):
    """Migration: rewrite every list from the list-passes' working shape
    (items: runs-dicts with an optional `sub` list) to the unified container
    shape — list > item > [paragraph leaf, nested list]. The passes keep
    their ergonomic runs-dict internals; this single pass is where the IR
    contract becomes one shape, so a list item can hold any node tomorrow."""
    def upgrade(node):
        for c in node.get("children") or []:
            upgrade(c)
        if node.get("type") != "list" or node.get("items") is None:
            return
        page, bbox, rk = node["page"], node["bbox"], node["rk"]
        children = []
        for it in node.pop("items"):
            if not isinstance(it, dict):
                it = {"text": it}
            sub = it.pop("sub", None)
            leaf = _leaf(ctx, "paragraph", it, page, bbox, rk)
            for k in ("refs", "breaks"):  # never drop a field when converting
                if it.get(k):
                    leaf[k] = it[k]
            kids = [leaf]
            if sub:
                sub_items = sub.get("items", [])
                sub_node = {"type": "list", "items": sub_items, "page": page,
                            "bbox": bbox, "rk": rk,
                            "nid": _stable_id("n", ctx.nids, "list", page, bbox,
                                              " ".join(_item_texts(sub_items)))}
                if sub.get("ordered"):
                    sub_node["ordered"] = sub["ordered"]
                if sub.get("start", 1) > 1:
                    sub_node["start"] = sub["start"]
                upgrade(sub_node)
                kids.append(sub_node)
            children.append(_container(ctx, "item", kids, page, bbox, rk))
        node["children"] = children
    for n in nodes:
        upgrade(n)
    return nodes


def _cat_runs(a, b):
    """Concatenate two runs-dicts with a joining space, shifting the second's
    style offsets. Either side may be None/empty; returns the other."""
    if not a or not a.get("text"):
        return b
    if not b or not b.get("text"):
        return a
    base = len(a["text"]) + 1
    out = {"text": a["text"] + " " + b["text"]}
    for k in _RUN_KEYS:
        runs = list(a.get(k) or []) + [[sp[0] + base, sp[1] + base, *sp[2:]]
                                       for sp in (b.get(k) or [])]
        if runs:
            out[k] = runs
    return out


def _slice_strip(runs, a, b):
    """_slice_runs with the slice bounds tightened past edge spaces."""
    t = runs.get("text", "")
    while a < b and t[a] == " ":
        a += 1
    while b > a and t[b - 1] == " ":
        b -= 1
    return _slice_runs(runs, a, b)


def _bullet_items(ctx, blk):
    """Split a bullet block into items, each carrying its own emphasis/link runs
    (a bold lead-in sentence or an inline link survives) judged against the
    whole block's dominant font. Unstyled items collapse to plain strings."""
    blk_font = _block_font(ctx, blk["lines"])
    groups = []
    for l in blk["lines"]:
        if l["text"][:1] in BULLETS:
            groups.append([l])
        elif groups:
            groups[-1].append(l)
    return [_strip_marker_item(_build_runs(ctx, blk, g, blk_font), BULLETS)
            for g in groups]


def _block_font(ctx, lines):
    """Char-weighted dominant font over `lines` — the reference weight/slant
    that emphasis is judged against."""
    dom_counts = Counter()
    for l in lines:
        dom_counts[l["fontIdx"]] += len(l["text"])
    return ctx.fonts[dom_counts.most_common(1)[0][0]]


def _block_base_rank(ctx, lines):
    """The LIGHTEST weight that covers a meaningful share (>=15%) of the block —
    the baseline emphasis is judged against. Lightest-significant (not dominant)
    means a bold lead-in stays <strong> even when it's the MAJORITY of the block
    (a long bold lede + short regular tail, as in numbered-action lists), while a
    block set uniformly in one heavier weight (a Medium callout) has no lighter
    weight present and so still yields no false emphasis."""
    counts = Counter()
    for l in lines:
        fc = [l["fontIdx"]] * len(l["text"])
        for s, e, fi in l.get("fontRuns", []):
            for i in range(s, min(e, len(fc))):
                fc[i] = fi
        for fi in fc:
            counts[fi] += 1
    total = sum(counts.values())
    if not total:
        return 400
    sig = [fi for fi, c in counts.items() if c >= 0.15 * total] or list(counts)
    return min(_font_weight_rank(ctx.fonts[fi]) for fi in sig)


def _join_block(ctx, blk, link_colors=()):
    """Join a block's lines into flowing text, dehyphenating soft wraps and
    carrying per-line superscript/link char ranges into the joined offsets.
    Text colored like the document's annotated links but lacking an annotation
    becomes a styled-link range (print PDFs often style cross-references as
    links without targets).
    Returns {"text", "sups": [[s,e]], "links": [[s,e,target]]}."""
    return _build_runs(ctx, blk, blk["lines"], _block_font(ctx, blk["lines"]),
                       link_colors)


def _build_runs(ctx, blk, lines, blk_font, link_colors=()):
    """Join `lines` (a whole block, or one list item's lines) into flowing text
    with per-char emphasis/link/sup/mark ranges. Emphasis is judged against
    `blk_font` — a run heavier than it is <strong>, an italic run is <em>. So a
    whole paragraph set in a heavier/italic weight is NOT emphasis (that's its
    role/style), while a bold word or an italic title inside regular prose is.
    Passing the WHOLE block's font as the reference while building one item at a
    time is what surfaces a bold lead-in sentence inside an otherwise-regular
    list item."""
    out = ""
    sups, links, emph, marks = [], [], [], []
    cspans = []  # colored-but-not-link runs (rubric §3: emphasis-by-color)
    line_joins = []  # offsets of the spaces where source lines were joined
    # baseline = the lighter of the dominant weight and the lightest-significant
    # weight, so a bold lede is caught even when it dominates the block
    blk_rank = min(_font_weight_rank(blk_font), _block_base_rank(ctx, lines))
    blk_italic = _font_is_italic(blk_font)

    def _strong(f):
        return _font_weight_rank(f) >= blk_rank + EMPH_GAP

    def _em(f):
        return _font_is_italic(f) and not blk_italic

    for l in lines:
        t = l["text"]
        if out.endswith("-") and t[:1].islower():
            ctx.log.entry("dehyphenate", page=blk["page"],
                          joined=out[-12:] + "|" + t[:12], block=blk["rk"])
            base = len(out) - 1
            out = out[:-1] + t
        elif out:
            line_joins.append(len(out))
            base = len(out) + 1
            out += " " + t
        else:
            base = 0
            out = t
        real = [[s + base, e + base, target]
                for s, e, target in l.get("links", [])]
        links.extend(real)
        sups.extend([s + base, e + base] for s, e in l.get("sups", []))

        # emphasis the standard way: a char is bold/italic iff its OWN font is
        # (from the font name + descriptor flags) — absolute, not relative to the
        # line/block dominant. Reconstruct the per-char font (line dominant,
        # overridden by the sub-line fontRuns), then emit maximal bold/italic
        # runs. This is what mature extractors (pdfminer/pdfplumber/PyMuPDF) do.
        fc = [l["fontIdx"]] * len(t)
        for s, e, fi in l.get("fontRuns", []):
            for i in range(s, min(e, len(t))):
                fc[i] = fi
        for kind, pred in (("strong", _strong), ("em", _em)):
            i = 0
            while i < len(t):
                # start a run only on a non-space emphasized char (so `i` always
                # advances past it — a leading bold space would never terminate)
                if t[i] == " " or not pred(ctx.fonts[fc[i]]):
                    i += 1
                    continue
                # extend over the same emphasis; interior spaces continue the run
                # so 'bold word' stays one span, then trim trailing spaces
                j = i + 1
                while j < len(t) and (pred(ctx.fonts[fc[j]]) or t[j] == " "):
                    j += 1
                while j > i + 1 and t[j - 1] == " ":
                    j -= 1
                emph.append([base + i, base + j, kind])
                i = j

        marks.extend([s + base, e + base, _hex(ctx.colors[ci])]
                     for s, e, ci in l.get("marks", []))

        styled = []
        if l["colorIdx"] in link_colors:
            styled.append([base, base + len(t)])
        else:
            styled.extend([s + base, e + base] for s, e, col in l.get("colors", [])
                          if col in link_colors)
        for s, e in styled:
            if not any(s < re_ and rs < e for rs, re_, _t in real):
                links.append([s, e, {"styled": True}])

        # colored-but-NOT-link inline runs (rubric §3): color used for emphasis.
        # Carried as [s, e, hex]; render promotes to <strong class="c-xxxxxx">
        # whose class restores the color. Link-colored runs became styled links
        # above; highlight fills are marks; this is the remainder.
        for s, e, col in l.get("colors", []):
            if col in link_colors:
                continue
            cspans.append([s + base, e + base, _hex(ctx.colors[col])])
    # merge adjacent same-kind emphasis (a phrase wrapped across lines)
    merged_emph = []
    for s, e, kind in sorted(emph):
        if merged_emph and s - merged_emph[-1][1] <= 1 \
                and merged_emph[-1][2] == kind:
            merged_emph[-1][1] = e
        else:
            merged_emph.append([s, e, kind])
    # merge adjacent same-color spans (a phrase wrapped across lines)
    merged_c = []
    for s, e, hx in sorted(cspans):
        if merged_c and s - merged_c[-1][1] <= 1 and merged_c[-1][2] == hx:
            merged_c[-1][1] = e
        else:
            merged_c.append([s, e, hx])
    return {"text": out, "sups": sups, "links": links,
            "emph": merged_emph, "marks": marks, "colors": merged_c,
            "lineJoins": line_joins}


def _link_colors(ctx, blocks):
    """Char colors the document uses for annotated link text (excluding the
    overall body color); used to spot link-styled text with no annotation."""
    body = Counter()
    linked = set()
    for blk in blocks:
        for l in blk["lines"]:
            body[l["colorIdx"]] += len(l["text"])
            for s, e, _t in l.get("links", []):
                hit = False
                for cs, ce, col in l.get("colors", []):
                    if cs < e and ce > s:
                        linked.add(col)
                        hit = True
                if not hit:
                    linked.add(l["colorIdx"])
    if body:
        linked.discard(body.most_common(1)[0][0])
    if linked:
        ctx.log.entry("link-colors", colors=sorted(linked))
    return linked


def _block_roles(pages, blocks):
    """(role, coverage) per block, by area-weighted vote of the tagged regions
    overlapping its bbox. (None, 0.0) when the page carries no tags."""
    out = []
    for blk in blocks:
        regs = pages[blk["page"]].get("tagged", [])
        bl, bb, br, bt = blk["bbox"]
        barea = max((br - bl) * (bt - bb), 1.0)
        votes = Counter()
        for l, b, r, t, role, *_seq in regs:  # tolerate the new order field
            ix = min(br, r) - max(bl, l)
            iy = min(bt, t) - max(bb, b)
            if ix > 0 and iy > 0:
                votes[role] += ix * iy
        if votes:
            role, _w = votes.most_common(1)[0]
            out.append((role, min(1.0, sum(votes.values()) / barea)))
        else:
            out.append((None, 0.0))
    return out


def _tag_heading_levels(ctx, roles):
    """Map the heading roles this document actually uses to dense levels
    starting at h1 (Title outranks H1 outranks H2…). Empty when the doc tags
    no headings, in which case size ranking is the only heading signal."""
    rank = {"Title": 0, "H": 1}
    used = {r for r, cov in roles
            if cov > 0.5 and (r in rank or re.fullmatch(r"H[1-6]", r or ""))}
    ordered = sorted(used, key=lambda r: rank.get(r, int(r[1:])))
    levels = {r: min(i + 1, 6) for i, r in enumerate(ordered)}
    if levels:
        ctx.log.entry("tag-heading-levels", mapping=levels)
    return levels


def _merge_cross_page_callouts(ctx, regions, pages):
    """A callout reaching the bottom of one page that resumes at the top of
    the next (same horizontal extent) is one box split by pagination."""
    regions = sorted(regions, key=lambda r: (r["page"], -r["bbox"][3]))
    out = []
    for reg in regions:
        prev = out[-1] if out else None
        if (prev is not None and prev["kind"] == "callout" and reg["kind"] == "callout"
                and reg["page"] == prev.get("endPage", prev["page"]) + 1):
            last_bbox = prev.get("lastBbox", prev["bbox"])
            prev_h = pages[prev.get("endPage", prev["page"])]["height"]
            cur_h = pages[reg["page"]]["height"]
            reaches_bottom = last_bbox[1] < 0.18 * prev_h
            resumes_top = reg["bbox"][3] > 0.78 * cur_h
            aligned = (abs(last_bbox[0] - reg["bbox"][0]) < 20
                       and abs(last_bbox[2] - reg["bbox"][2]) < 20)
            if reaches_bottom and resumes_top and aligned:
                ctx.log.entry("merge-callout-pages", from_page=prev["page"],
                              to_page=reg["page"], region=prev["rk"],
                              continued=reg["rk"])
                prev["blockIdx"] = sorted(prev["blockIdx"] + reg["blockIdx"])
                prev["endPage"] = reg["page"]
                prev["lastBbox"] = reg["bbox"]
                continue
        out.append(reg)
    return out


def _indents(ctx, nodes):
    """Page-geometry pass: paragraphs offset from the page's prevailing
    left edge are centered when their margins balance (single lines too -
    _block_align can't judge those), otherwise indented. Indents are a
    converter choice (question), preservable per paragraph or document-wide
    (structure.indents / indentOverrides); web convention removes them."""
    by_page = {}
    for n in nodes:
        if n["type"] == "paragraph" and not (n.get("data") or {}).get("align"):
            by_page.setdefault(n["page"], []).append(n)
    default = ctx.cfg["structure"].get("indents", "remove")
    overrides = ctx.cfg["structure"].get("indentOverrides", [])
    found = []
    for page_n, paras in by_page.items():
        if len(paras) < 3:
            continue
        base = Counter(round(n["bbox"][0]) for n in paras).most_common(1)[0][0]
        right = max(n["bbox"][2] for n in paras)
        for n in paras:
            size = (n.get("data") or {}).get("size") or 10.0
            ind = n["bbox"][0] - base
            rm = right - n["bbox"][2]
            # centered = pulled in from BOTH sides by similar amounts. Require a
            # real right margin too (a left-indented block that still runs to the
            # full right edge — rm≈0 — is indented body, not centered), and a
            # tight absolute balance (the old 10%-of-width tolerance was ~46pt,
            # so it mislabeled left-indented continuations as centered).
            if ind > 2 * size and rm > 2 * size and abs(ind - rm) < 1.5 * size:
                n["data"]["align"] = "center"
                ctx.log.entry("centered", page=page_n, nid=n["nid"],
                              text=(n.get("text") or "")[:50])
                continue
            if not (0.8 * size <= ind <= 6 * size):
                continue
            em = round(ind / size, 1)
            ov = _override_for(overrides, n["text"])
            mode = ov.get("mode", default) if ov is not None else default
            ctx.log.entry("indent", page=page_n, nid=n["nid"], em=em,
                          mode=mode, text=n["text"][:60])
            n["data"]["indent"] = em
            if mode == "preserve":
                n["data"]["indentKeep"] = True
            found.append((n, mode))
    # indent-heavy documents (questionnaires, outlines) would flood the
    # panel; their lever is document-wide config until question grouping
    if len(found) <= 8:
        for n, mode in found:
            _question(ctx, "indent", n,
                      f"“{n['text'][:50]}…” is indented in the source. Keep "
                      "the indent, or flush left (web convention)?",
                      ["preserve", "remove"], mode)


TOC_TITLE = re.compile(
    r"(table of )?contents|what.?s inside|in this (report|issue|guide)", re.I)
# a block whose whole text is just a 1-3 digit page number (the number column)
_TOC_NUM = re.compile(r"0?\d{1,3}$")
# an entry line that opens with a page number then a capitalized title
_TOC_LEADNUM = re.compile(r"^\s*0?\d{1,3}\s+[A-Z0-9“‘(]")


def _toc_pages(ctx, pages, blocks):
    """TOC bands per page: many dot-leader lines, or a 'Contents' title plus
    several lines ending in page numbers. Only the vertical band spanned by
    those lines is dropped - the title and group labels sandwiched between
    entries go with it, but content sharing the page (a TOC that ends
    mid-page) survives. Navigation is reconstructed from our heading tree."""
    bands = {}
    npages = len(pages)
    for p in pages.values():
        page_blocks = [blk for blk in blocks if blk["page"] == p["n"]]
        lines = [l["text"] for blk in page_blocks for l in blk["lines"]]
        leader = sum(1 for t in lines if re.search(r"\.{3,}\s*\d{1,3}$", t))
        trailing = sum(1 for t in lines if re.search(r"\s\d{1,3}$", t))
        titled = any(TOC_TITLE.fullmatch(t.strip()) for t in lines)
        # designed TOCs carry page numbers in a separate aligned column
        # (numeric-only blocks) or as a leading token, with NO dot leaders —
        # invisible to the trailing-number tests above.
        def _blk_text(blk):
            return " ".join(l["text"] for l in blk["lines"]).strip()
        nums = []
        numcol = leadnum = 0
        for blk in page_blocks:
            t = _blk_text(blk)
            if _TOC_NUM.fullmatch(t):
                numcol += 1
                nums.append(int(t))
            for l in blk["lines"]:
                m = _TOC_LEADNUM.match(l["text"])
                if m:
                    leadnum += 1
                    nums.append(int(re.match(r"\s*(0?\d{1,3})", l["text"]).group(1)))
        # real page numbers can't exceed the doc, and they SPREAD across it with
        # gaps; an endnote/list sequence (1,2,3…) is dense (range ≈ count) and
        # data values are out of range — both are excluded here, which is what
        # kept this off endnote pages and figure data.
        pages_like = [v for v in nums if 1 <= v <= npages]
        spread = (len(pages_like) >= 4
                  and max(pages_like) - min(pages_like) > len(pages_like))
        # and only near the front (TOCs live in the first few pages) unless a
        # TOC title explicitly anchors it
        designed = spread and (titled or p["n"] <= 7)
        if not (leader >= 5 or (titled and trailing >= 3) or designed):
            continue

        def tocish(blk):
            if _TOC_NUM.fullmatch(_blk_text(blk)) or TOC_TITLE.fullmatch(_blk_text(blk)):
                return True
            return any(re.search(r"\.{3,}\s*\d{1,3}$|\s\d{1,3}$", l["text"])
                       or _TOC_LEADNUM.match(l["text"]) for l in blk["lines"])
        marks = [blk for blk in page_blocks if tocish(blk)]
        if not marks:
            continue
        bot = min(blk["bbox"][1] for blk in marks) - 2
        top = max(blk["bbox"][3] for blk in marks) + 2
        bands[p["n"]] = (bot, top)
        ctx.log.entry("toc-page", page=p["n"], leader_lines=leader,
                      trailing_num_lines=trailing, numcol=numcol, leadnum=leadnum,
                      titled=titled, band=[round(bot, 1), round(top, 1)])
    return bands


# the (?!\d) guard rejects decimals: "0.3% - 0.7%" (chart labels) and
# "10.1073/…" (wrapped DOIs) must not read as note markers 0 and 10
NOTE_START = re.compile(r"^(\d{1,3})(?:[.)]\s*(?!\d)|\s+)(?=\S)")
# plain (non-superscript) LETTER designators: "f Note: Funding data…" at the
# foot of cleanair p15 — a single lowercase letter + separator. Ambiguity
# with prose ("a series of…") is carried by the downstream gates: small size,
# position/citation signal, and the marker SEQUENCE
LETTER_NOTE_START = re.compile(r"^([a-z])(?:[.)]\s*|\s+)(?=\S)")


def _merge_sup_ranges(text, sups):
    """Roman markers like 'ii' often arrive as separate single-char sup runs
    separated only by spaces; merge such neighbors into one range."""
    merged = []
    for s, e in sorted(sups):
        if merged and s - merged[-1][1] <= 1 \
                and text[merged[-1][1]:s].strip() == "":
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return merged


def _extract_refs(text, sups):
    """In-text footnote references from superscript ranges — the SINGLE source
    of ref detection, applied to every text unit (paragraph, list item, table
    cell, caption), never gated to one node type. A reference is a superscript
    that parses to a marker value; a multi-citation superscript ("20, 21") is
    one range holding several, split so each links and reconciles."""
    refs = []
    for s, e in _merge_sup_ranges(text, sups or []):
        seg = text[s:e]
        # a superscript 'o' wedged between a digit and C/F is a typeset degree
        # sign ("34oC day", "1.5oC."), not a lettered note reference
        if seg.strip().lower() == "o" and s > 0 and text[s - 1].isdigit() \
                and text[e:e + 1] in ("C", "F"):
            continue
        val = _marker_value(seg.replace(" ", "")) if e - s <= 7 else None
        if val:
            refs.append([s, e, val])
        elif re.fullmatch(r"\d{1,3}(?:\s*,\s*\d{1,3})+", seg):
            for m in re.finditer(r"\d{1,3}", seg):
                refs.append([s + m.start(), s + m.end(), int(m.group())])
    return refs


def _attach_refs(tree):
    """Attach footnote refs to EVERY text-bearing unit in the IR — paragraph,
    heading, list item, table cell, caption, aside, or any node type that ever
    exists — computed from its `sups`, then drop the raw `sups`.

    This is a fully GENERIC walk: it descends into every dict value and every
    list element and inspects every dict, with no list of node types or
    container keys. Enumerating "the places refs can live" is the bug this
    replaces — refs are a property of text, so anything holding (text, sups)
    gets them, and a new node type can never fall through. [[first-class-content]]"""
    def visit(u):
        if isinstance(u, dict):
            if "text" in u and u.get("sups") and not u.get("refs"):
                refs = _extract_refs(u["text"], u["sups"])
                if refs:
                    u["refs"] = refs
            u.pop("sups", None)
            for v in u.values():
                visit(v)
        elif isinstance(u, list):
            for v in u:
                visit(v)
    visit(tree)


def _line_marker(line):
    """Leading footnote marker of a line: (value, raw, text_offset, is_sup).
    A superscript run at position 0 (arabic or roman) is the strongest form;
    otherwise the plain numbered-line regex."""
    text = line["text"]
    for s, e in _merge_sup_ranges(text, line.get("sups", [])):
        if s == 0 and 0 < e <= 7:
            val = _marker_value(text[:e].replace(" ", ""))
            if val:
                return val, text[:e].replace(" ", ""), e, True
            break
    m = NOTE_START.match(text)
    if m:
        return int(m.group(1)), m.group(1), m.end(), False
    m = LETTER_NOTE_START.match(text)
    if m:
        return (_ALPHA_NOTE_BASE + ord(m.group(1)) - 96, m.group(1),
                m.end(), False)
    return None
NOTES_HEADING = re.compile(r"(end\s*)?notes?|references|sources", re.I)


_CITE_RE = re.compile(r"https?://|www\.|\b(?:19|20)\d{2}\b")


def _noteish_block(blk, text):
    """Note-shaped block: leads with a marker that is superscript or backed by
    a citation signal — or, the detached-first-marker form (gates p9), at
    least two interior lines lead with markers and the block cites. Chart
    legends and numbered lists fail the citation gate."""
    nm = _line_marker(blk["lines"][0])
    if nm:
        return bool(nm[3] or _CITE_RE.search(text))
    return (sum(1 for l in blk["lines"][1:] if _line_marker(l)) >= 2
            and bool(_CITE_RE.search(text)))


def _seq_count(blk, expected):
    """Sequential markers inside one block, continuing `expected` (or starting
    fresh): (count, next expected). Mirrors _parse_notes' walk without logging."""
    count = 0
    for l in blk["lines"]:
        m = _line_marker(l)
        if m and (expected is None or m[0] in (expected, expected + 1)):
            count += 1
            expected = m[0] + 1
    return count, expected


def _body_note_runs(ctx, blocks, texts, skip, body_size):
    """Endnote sections set at BODY size — the form the small-text gate can't
    see (points-of-light: "35 Suzanne Blake …" at 10.5pt body). A run of
    consecutive blocks whose leading markers count straight through, holding
    ≥4 notes, where the text carries a real CITATION signal (years/URLs in at
    least half the notes) is a notes section regardless of size or heading.
    The citation gate is what keeps numbered LISTS and survey questions out
    (respond-to-crisis's appendix questions count sequentially but cite
    nothing). Returns (sectionish, scattered) member index sets: BODY-size
    chains read as an endnotes SECTION (they anchor the rendered position);
    small chains are scattered page notes (collected, but never an anchor)."""
    member = {}       # block index -> its run's START block (group identity)
    scattered = set()
    idxs = [i for i in range(len(blocks)) if i not in skip]
    k = 0
    while k < len(idxs):
        i = idxs[k]
        first = _line_marker(blocks[i]["lines"][0])
        if not (first and _dominant_size(blocks[i]) <= 1.05 * body_size):
            k += 1
            continue
        count, expected = _seq_count(blocks[i], None)
        chain = [i]
        j = k + 1
        misses = 0  # sidebar layouts interleave body blocks between the notes
        while j < len(idxs) and misses <= 3:
            nb = idxs[j]
            m = _line_marker(blocks[nb]["lines"][0])
            if not (m and m[0] in (expected, expected + 1)
                    and _dominant_size(blocks[nb]) <= 1.05 * body_size):
                misses += 1  # skip the interloper; the chain may resume
                j += 1
                continue
            misses = 0
            c2, expected = _seq_count(blocks[nb], expected)
            count += c2
            chain.append(nb)
            j += 1
        # a body-size run needs bulk (4+) to be believed; a run of SMALL blocks
        # is already footnote-shaped, so a pair suffices (cleanair's per-page
        # letter notes f+g)
        small = all(_dominant_size(blocks[c]) <= 0.92 * body_size for c in chain)
        if count >= (2 if small else 4):
            cites = len(_CITE_RE.findall(" ".join(texts[c] for c in chain)))
            if cites >= 0.5 * count:
                if small:
                    scattered.update(chain)
                else:
                    for c in chain:
                        member[c] = chain[0]
                ctx.log.entry("note-run", page=blocks[i]["page"], blocks=len(chain),
                              notes=count, cites=cites, small=small,
                              text=texts[i][:60])
        k = max(j, k + 1)
    return member, scattered


def _block_fragments(blk, block_idx):
    """A block's lines as ordered note fragments. A line that leads with a
    marker becomes (marker value, raw, text-after-marker); any other line is a
    (None) continuation. The sequencer decides which markers are real."""
    out = []
    for l in blk["lines"]:
        m = _line_marker(l)
        if m:
            out.append({"page": blk["page"], "block": block_idx, "rk": blk["rk"],
                        "marker": m[0], "raw": m[1], "text": l["text"][m[2]:]})
        else:
            out.append({"page": blk["page"], "block": block_idx, "rk": blk["rk"],
                        "marker": None, "raw": None, "text": l["text"]})
    return out


def _accept_marker(M, last, last_page, page, next_marker):
    """Is marker M the next note, given the last accepted note number/page and
    the very next marker in the stream? Notes are a MONOTONIC subsequence:
      - first marker: yes.
      - M <= last: a backward marker is a per-page RESTART if we've turned the
        page (toolkit numbers 1,2,3 on every page), else a misread / column
        scramble on the same page (reject).
      - small forward gap: yes (a note or two legitimately missing).
      - big forward jump: real only if the sequence continues FROM it. If the
        NEXT marker instead resumes just after `last`, the jump is an outlier —
        a digit misread ("277"->"287") followed by the true 278 — so reject it.
        This is what stops one bad marker swallowing the rest into a runaway."""
    if last is None:
        return True
    if M <= last:
        return page != last_page
    if M <= last + _NOTE_SMALLGAP:
        return True
    if next_marker is not None and last < next_marker <= last + _NOTE_SMALLGAP:
        return False
    return True


def _sequence_notes(ctx, frags):
    """Build note records from an ordered fragment stream. A note's text runs
    from its accepted marker to the next accepted marker; rejected markers and
    markerless lines fold into the current note as continuation.

    Detached-marker recovery: fragments that LEAD a block with no marker are
    buffered rather than folded immediately. When the block's first accepted
    marker M shows exactly ONE number missing (last accepted == M-2, or M == 2
    at the very start), the buffered lines ARE that missing note — its marker
    was typeset apart (glued into a chart) — by sequence arithmetic, not
    guessing (gates p9: notes 1 and 9 head their panels markerless). Any other
    gap folds the buffer into the current note as ordinary continuation.
    Returns (notes, contributing block indexes)."""
    n = len(frags)
    next_marker, nxt = [None] * n, None
    for k in range(n - 1, -1, -1):
        next_marker[k] = nxt
        if frags[k]["marker"] is not None:
            nxt = frags[k]["marker"]
    notes, contributing = [], set()
    last = last_page = cur = None
    pending = []          # markerless fragments leading the current block
    folds = []            # rejected markers folded into a note (split later)
    cur_block, block_had_marker = None, False

    def fold_pending():
        nonlocal pending
        if cur is not None:
            for p in pending:
                cur["text"] += " " + p["text"]
                contributing.add(p["block"])
        pending = []

    for k, fr in enumerate(frags):
        if fr["block"] != cur_block:
            fold_pending()   # a block with no markers was pure continuation
            cur_block, block_had_marker = fr["block"], False
        M = fr["marker"]
        if M is None:
            if not block_had_marker:
                pending.append(fr)
            elif cur is not None:
                cur["text"] += " " + fr["text"]
                contributing.add(fr["block"])
            continue
        if _accept_marker(M, last, last_page, fr["page"], next_marker[k]):
            if pending and (last == M - 2 or (last is None and M == 2)):
                p0 = pending[0]
                rk = ctx.log.entry("note-inferred", page=p0["page"], n=M - 1,
                                   block=p0["rk"],
                                   text=pending[0]["text"][:80],
                                   reason="block-leading text + single gap")
                cur = {"n": M - 1, "marker": str(M - 1), "page": p0["page"],
                       "text": " ".join(p["text"] for p in pending).strip(),
                       "rk": rk}
                notes.append(cur)
                contributing.update(p["block"] for p in pending)
                pending = []
            else:
                fold_pending()
            block_had_marker = True
            rk = ctx.log.entry("note", page=fr["page"], n=M, marker=fr["raw"],
                               block=fr["rk"], text=fr["text"][:80])
            cur = {"n": M, "marker": fr["raw"], "page": fr["page"],
                   "text": fr["text"].lstrip(".) ").strip(), "rk": rk}
            notes.append(cur)
            last, last_page = M, fr["page"]
            contributing.add(fr["block"])
        else:
            fold_pending()
            block_had_marker = True
            ctx.log.entry("note-reject", page=fr["page"], rejected_n=M,
                          last=last, text=fr["text"][:60])
            if cur is not None:
                folds.append({"note": cur, "off": len(cur["text"]),
                              "raw": fr["raw"], "block": fr["block"],
                              "page": fr["page"]})
                cur["text"] += " " + fr["raw"] + " " + fr["text"]
                contributing.add(fr["block"])
    fold_pending()
    _split_misread_folds(ctx, notes, folds, contributing)
    return notes, contributing


def _split_misread_folds(ctx, notes, folds, contributing):
    """Recover a note whose printed marker was MISREAD by one glyph (gates:
    '200' extracted as '209'; the sequencer rightly rejected 209 between 199
    and 201 and folded its text into note 199). When a note's number + 1 is
    missing from the collected set and exactly one rejected marker was folded
    into it whose digits differ from the missing value in ONE position, the
    folded text IS the missing note — sequence arithmetic again, not a guess.
    Splits the fold back out in place."""
    by_note = {}
    for f in folds:
        by_note.setdefault(id(f["note"]), []).append(f)
    collected = Counter(nt["n"] for nt in notes)
    for nt in list(notes):
        fs = by_note.get(id(nt), [])
        want = nt["n"] + 1
        if len(fs) != 1 or collected[want]:
            continue
        f = fs[0]
        raw = f["raw"]
        wraw = str(want)
        if not raw.isdigit() or len(raw) != len(wraw) \
                or sum(a != b for a, b in zip(raw, wraw)) != 1:
            continue
        tail = nt["text"][f["off"]:].strip()
        if not tail.startswith(raw):
            continue
        text = tail[len(raw):].lstrip(".) ").strip()
        if not text:
            continue
        rk = ctx.log.entry("note-split-misread", page=f["page"], n=want,
                           misread=raw, from_note=nt["n"], text=text[:80])
        nt["text"] = nt["text"][:f["off"]].rstrip()
        notes.insert(notes.index(nt) + 1,
                     {"n": want, "marker": wraw, "page": f["page"],
                      "text": text, "rk": rk})
        collected[want] += 1
        contributing.add(f["block"])


def _find_notes(ctx, pages, blocks, texts, skip, body_size):
    """Footnote/endnote text in three forms: numbered blocks following a
    notes-section heading, small numbered text at the bottom of a page, or a
    body-size sequential run with citation signal (_body_note_runs). Candidate
    blocks are flattened to fragments and sequenced (_sequence_notes) so a bad
    marker can never poison the rest of the run.
    Returns (notes, contributing block indexes, in-place position)."""
    # Placement is deterministic (user's rule): the notes live WHERE WE FOUND
    # their content — no heading match, no majority vote.
    body_runs, small_runs = _body_note_runs(ctx, blocks, texts, skip, body_size)
    frags = []
    in_section = False
    for i, (blk, text) in enumerate(zip(blocks, texts)):
        if i in skip:
            continue
        size = _dominant_size(blk)
        if NOTES_HEADING.fullmatch(text.strip()):
            in_section = True  # Endnotes/Sources/References label starts a run
            continue
        marker = _line_marker(blk["lines"][0])
        cand = False
        if not in_section and (i in body_runs or i in small_runs):
            cand = True
        elif in_section:
            if size > body_size * 1.15:
                in_section = False  # a larger heading ends the notes section
            elif marker:
                cand = True
            elif frags and len(text.strip()) <= 4:
                cand = True  # tiny stray fragment (split subscript) stays
            elif frags and size < body_size * 1.15 and (
                    any(_line_marker(l) for l in blk["lines"])
                    or text[:1].islower()):
                cand = True  # holds a note, or wraps the previous one
            else:
                in_section = False
        if not cand and not in_section and size <= 0.92 * body_size:
            page = pages[blk["page"]]
            if marker:
                # bottom of the page; or a leading-superscript marker anywhere;
                # or a small block carrying a citation signal (sidebar notes)
                if (blk["bbox"][1] < 0.18 * page["height"] or marker[3]
                        or _CITE_RE.search(text)):
                    cand = True
            elif (sum(1 for l in blk["lines"][1:] if _line_marker(l)) >= 2
                    and _CITE_RE.search(text)):
                # a notes panel whose FIRST note's marker was detached (glued
                # into a chart): leading lines are continuation text, but the
                # interior lines still lead with markers and the block cites
                # (gates p9: notes 1-8 in one block, the '1' lost to a chart)
                cand = True
        if cand:
            frags.extend(_block_fragments(blk, i))
    notes, note_idx = _sequence_notes(ctx, frags)
    # (page, n): keeps doc-wide numbering in order AND keeps per-page
    # RESTARTING footnotes (toolkit: 1, 2, 3 on every page) in document order
    # instead of interleaving every page's "1" together
    notes.sort(key=lambda n: (n["page"], n["n"]))
    # Placement (user's rule): the notes live where their content was found —
    # the FIRST note block, in reading order. The one exception is per-page
    # restarting footnotes (toolkit: 1,2,3 at the bottom of every page): those
    # are scattered across many pages, so no single in-place location makes
    # sense — they render only in the end-of-document data copy (place=None).
    place = None
    if notes:
        n_counts = Counter(n["n"] for n in notes)
        pages_with = sorted({n["page"] for n in notes})
        restart = any(c > 1 for c in n_counts.values())
        # A single in-place location only makes sense when the notes live in ONE
        # place: on one page, or a contiguous run of pages (a real endnotes
        # section that may be followed by appendices). When they're SCATTERED
        # across the document (per-page figure notes on p13, p15, p17 … plus
        # endnotes on p33-35, as in clean-air) there is no single spot — placing
        # all of them at the earliest one would inject the whole pile mid-text,
        # the exact bug we're removing. Those render only in the end data copy;
        # correct per-page placement is the deferred follow-up.
        span = pages_with[-1] - pages_with[0]
        contiguous = span <= len(pages_with)
        if not restart and contiguous:
            place = min(note_idx,
                        key=lambda i: (blocks[i]["page"], -blocks[i]["bbox"][3]))
    return notes, note_idx, place


def _fn_display(val):
    """Human label for a note index value: letters live at _ALPHA_NOTE_BASE+n."""
    if val > _ALPHA_NOTE_BASE:
        return chr(val - _ALPHA_NOTE_BASE + 96)
    return str(val)


def _reconcile_notes(ctx, nodes, notes):
    """Compare in-text reference indexes against collected note indexes, both
    directions. Returns a `flag` node (rendered as a top-of-document banner)
    when they don't fully match, else None. This is the QA check the user asked
    for: 'does every reference and every note have a match?'"""
    ref_vals = set()

    def visit(u):
        if not isinstance(u, dict):
            return
        for r in (u.get("refs") or []):
            ref_vals.add(r[2])
        for child in (u.get("children") or []):
            visit(child)
        for it in (u.get("items") or []):
            visit(it)
            sub = it.get("sub") if isinstance(it, dict) else None
            if sub:
                for s in (sub.get("items") or []):
                    visit(s)
    for n in nodes:
        visit(n)

    note_vals = {n["n"] for n in notes}
    refs_no_note = sorted(v for v in ref_vals if v not in note_vals)
    notes_no_ref = sorted(v for v in note_vals if v not in ref_vals)
    if not refs_no_note and not notes_no_ref:
        return None

    rk = ctx.log.entry("footnote-mismatch",
                       refs_without_notes=[_fn_display(v) for v in refs_no_note],
                       notes_without_refs=[_fn_display(v) for v in notes_no_ref],
                       ref_total=len(ref_vals), note_total=len(note_vals))
    return {"type": "flag", "kind": "footnote-mismatch",
            "refs_no_note": [_fn_display(v) for v in refs_no_note],
            "notes_no_ref": [_fn_display(v) for v in notes_no_ref],
            "page": 1, "bbox": [0, 0, 0, 0], "rk": rk, "data": {},
            "nid": _stable_id("n", ctx.nids, "flag", 0, [0, 0, 0, 0],
                              "footnote-mismatch")}


def _heading_id(text, used):
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "section"
    hid, i = base, 1
    while hid in used:
        i += 1
        hid = f"{base}-{i}"
    used.add(hid)
    return hid
