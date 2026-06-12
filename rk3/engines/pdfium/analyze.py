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

VERSION = 35


def _font_emphasis(name, weight, base_name):
    """'strong'/'em' when this font is a bold/italic variant the base isn't."""
    low = (name or "").lower()
    base = (base_name or "").lower()

    def bold(s):
        return any(k in s for k in ("bold", "black", "semibold", "heavy"))

    def italic(s):
        return "italic" in s or "oblique" in s

    if italic(low) and not italic(base):
        return "em"
    if (bold(low) or weight >= 600) and not bold(base):
        return "strong"
    return None

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


def _marker_value(raw):
    """Footnote marker -> int (arabic or roman), else None."""
    raw = raw.strip().rstrip(".)").strip()
    if raw.isdigit() and len(raw) <= 3:
        return int(raw)
    return ROMAN.get(raw.lower())

BULLETS = "•◦▪‣–—-*·§"
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


def run(ctx):
    asm = ctx.artifact("assemble")
    blocks, fonts, colors = asm["blocks"], asm["fonts"], asm["colors"]
    pages = {p["n"]: p for p in asm["pages"]}
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
    toc_pages = _toc_pages(ctx, pages, blocks) if drop_toc else set()
    skip = {i for i, blk in enumerate(blocks) if blk["page"] in toc_pages}
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
            # Substantial mid-page text is content regardless of the tag.
            page = pages[blk["page"]]
            edge = (blk["bbox"][1] < 0.12 * page["height"]
                    or blk["bbox"][3] > 0.88 * page["height"])
            if edge or len(texts[i]) <= 80:
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
    regions = _detect_regions(ctx, pages, blocks, texts, body_size, toc_pages,
                              top_size)
    regions = _merge_cross_page_callouts(ctx, regions, pages)
    absorbed = {}  # block index -> region
    for reg in regions:
        for bi in reg["blockIdx"]:
            absorbed[bi] = reg
    _find_captions(ctx, regions, blocks, texts, absorbed, body_size, roles)
    absorbed.update(dict.fromkeys(skip))

    notes, note_idx, notes_sectioned = _find_notes(ctx, pages, blocks, texts,
                                                   absorbed, body_size)
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

    for page_n, items in page_items.items():
        bboxes = [item_bbox(it) for it in items]
        split = _column_split(bboxes)
        if split is not None:
            page_items[page_n] = _flow_order(items, bboxes, split)
            ctx.log.entry("two-column", page=page_n, split=round(split, 1))

    deepest = max([*tag_levels.values(), *levels.values(), 0])
    kicker_level = min(deepest + 1, 6) if deepest else 0

    nodes = []
    used_ids = set()
    fig_count = 0
    for page_n in sorted(page_items):
        for kind, ref in page_items[page_n]:
            if kind == "block":
                nodes.append(_block_node(ctx, blocks[ref], rich[ref], fonts,
                                         levels, body_size, used_ids,
                                         role=roles[ref], tag_levels=tag_levels,
                                         kicker_level=kicker_level))
            else:
                if ref["kind"] == "figure":
                    fig_count += 1
                    node = _figure_node(ctx, ref, pages, fig_count)
                else:
                    node = _try_table(ctx, ref, blocks, texts, pages)
                    if node is None:
                        node = _aside_node(ctx, ref, blocks, rich, fonts,
                                           body_size, roles)
                        fig_count = _aside_images(ctx, ref, node, pages,
                                                  fig_count)
                nodes.append(node)
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

    # figure regions absorb their text into the cropped image
    for reg in regions:
        if reg["kind"] == "figure":
            for bi in reg["blockIdx"]:
                ctx.audit_claimed[blocks[bi]["page"]] += _alnum(texts[bi])

    nodes = _group_tag_lists(ctx, nodes)
    nodes = _group_bullet_paragraphs(ctx, nodes)
    # sentences interrupted by page breaks happen in the main flow too,
    # not just inside callouts
    nodes = _join_pagebreak_sentences(ctx, nodes)
    nodes = _aside_layout_and_pullquotes(ctx, nodes)

    if notes:
        last = blocks[max(note_idx)]
        rk = ctx.log.entry("footnotes", count=len(notes),
                           numbers=[n["n"] for n in notes][:20],
                           sectioned=notes_sectioned)
        node = {"type": "footnotes", "notes": notes, "page": last["page"],
                "bbox": last["bbox"], "rk": rk, "data": {}}
        node["nid"] = _stable_id("n", ctx.nids, "footnotes", node["page"],
                                 node["bbox"], "footnotes")
        if notes_sectioned:
            # notes lifted from a section render AT the section's position
            # (an Endnotes section may be followed by Sources etc.); only
            # scattered page-bottom notes collect at document end
            first = min(note_idx, key=lambda i: (blocks[i]["page"],
                                                 -blocks[i]["bbox"][3]))
            key = (blocks[first]["page"], -blocks[first]["bbox"][3])
            pos = next((k for k, n in enumerate(nodes)
                        if (n["page"], -n["bbox"][3]) > key), len(nodes))
            nodes.insert(pos, node)
        else:
            nodes.append(node)

    title = next((n["text"] for n in nodes if n["type"] == "heading" and n["level"] == 1),
                 ctx.source.stem)
    audit = _audit(ctx, blocks, texts, nodes)
    ctx.write_artifact("analyze", {
        "title": title,
        "pages": {str(p["n"]): [p["width"], p["height"]] for p in asm["pages"]},
        "questions": ctx.questions,
        "audit": audit,
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
        out[page] += sum(_alnum(c) for row in n.get("rows", []) for c in row)
        out[page] += _alnum(n.get("caption"))
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

    # user answers (region overrides from config) trump every heuristic
    for ov in ctx.cfg["structure"].get("regionOverrides", []):
        if ov.get("page") == page["n"] and _overlap_frac(bbox, ov["bbox"]) > 0.5:
            kind = ov["kind"]
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
    """Per-side accent borders: stroked path segments tell us WHICH sides a
    box outline actually draws; thin filled bars hugging an edge count too.
    Returns {side: [colorIdx, width_pt]} only for partial borders."""
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
        # stroked outline with segment data
        if o[8] and len(o) > 10 and o[10] and o[6] is not None:
            sides = _seg_sides(o[10], (o[1], o[2], o[3], o[4]),
                               max(4.0, (o[9] or 1.0)))
            if 0 < len(sides) < 4:
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
                # small font as the only signal => genuinely unsure
                reg["captionWeak"] = not (keyword or tagged_caption)
                reg["captionBlock"] = blk["rk"]
                absorbed[i] = reg
                ctx.log.entry("caption", page=reg["page"], figure=reg["rk"],
                              gap=round(gap, 1), text=text[:80])
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

def _heading_node(ctx, blk, text, level, reason, prov, used_ids):
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
        ctx.log.entry("section-number", page=blk["page"], num=num,
                      mode=mode, text=rest[:60])
    hid = _heading_id(text, used_ids)
    rk = ctx.log.entry("heading", level=level, page=blk["page"],
                       bbox=blk["bbox"], size=prov["size"], reason=reason,
                       text=text[:120], block=blk["rk"])
    node = {"type": "heading", "level": level, "text": text, "id": hid,
            "page": blk["page"], "bbox": blk["bbox"], "rk": rk, "data": prov,
            "nid": _stable_id("n", ctx.nids, "heading", blk["page"],
                              blk["bbox"], text)}
    if num and ctx.cfg["structure"].get("sectionNumbers", "styled") == "styled":
        node["sectionNum"] = num
    return node


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
    font = fonts[blk["lines"][0]["fontIdx"]]
    prov = {"font": font["name"], "weight": font["weight"], "size": size}
    color_votes = Counter()
    for l in blk["lines"]:
        color_votes[l["colorIdx"]] += len(l["text"])
    if color_votes:
        prov["color"] = _hex(ctx.colors[color_votes.most_common(1)[0][0]])
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
                                 prov, used_ids)
        tag_levels = None   # forced paragraph: fall through, skip heading paths
        levels = {}
        kicker_level = 0

    if not in_aside and tag_levels and tag_role in tag_levels and tag_cov > 0.5 \
            and text.strip():
        return _heading_node(ctx, blk, text, tag_levels[tag_role],
                             f"struct tag {tag_role} (coverage {tag_cov:.2f})",
                             prov, used_ids)

    if not in_aside and size in levels and _looks_like_heading(text):
        level = levels[size]
        # authors tag genuine headings as P often enough that a P tag must
        # not veto strong size evidence — but the disagreement is exactly
        # what the question system is for
        conflict = bool(tag_levels) and tag_role == "P" and tag_cov > 0.5
        reason = f"size {size} ranked #{level} above body {body_size}"
        if conflict:
            reason += " (struct tag says P — kept as heading, question emitted)"
        node = _heading_node(ctx, blk, text, level, reason, prov, used_ids)
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
                             prov, used_ids)

    if not in_aside and kicker_level and len(blk["lines"]) == 1 \
            and NOTES_HEADING.fullmatch(text.strip()):
        # section labels like "Sources" deserve a heading even at body size
        return _heading_node(ctx, blk, text, kicker_level,
                             "notes-section label", prov, used_ids)

    if _is_bullet_list(blk):
        items = _bullet_items(blk)
        rk = ctx.log.entry("list", page=blk["page"], bbox=blk["bbox"],
                           items=len(items),
                           reason="opens with a bullet; unbulleted lines are wraps",
                           block=blk["rk"])
        prov["marker"] = blk["lines"][0]["text"][:1]
        node = {"type": "list", "items": items, "page": blk["page"],
                "bbox": blk["bbox"], "rk": rk, "data": prov}
        node["nid"] = _stable_id("n", ctx.nids, "list", node["page"],
                                 node["bbox"], " ".join(items))
        return node

    ol = _ordinal_block(blk)
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
    refs = []
    for s, e in _merge_sup_ranges(text, rich.get("sups", [])):
        val = _marker_value(text[s:e].replace(" ", "")) if e - s <= 7 else None
        if val:
            refs.append([s, e, val])
    rk = ctx.log.entry("paragraph", page=blk["page"], bbox=blk["bbox"],
                       size=size, strong=strong, refs=[r[2] for r in refs],
                       links=len(rich.get("links", [])),
                       text=text[:120], block=blk["rk"])
    node = {"type": "paragraph", "text": text, "page": blk["page"],
            "bbox": blk["bbox"], "rk": rk, "data": prov}
    node["nid"] = _stable_id("n", ctx.nids, "paragraph", node["page"],
                             node["bbox"], text)
    if strong:
        node["strong"] = True
    if refs:
        node["refs"] = refs
    if rich.get("links"):
        node["links"] = rich["links"]
    if rich.get("emph"):
        node["emph"] = rich["emph"]
    brk_ov = _override_for(ctx.cfg["structure"].get("breakOverrides", []), text)
    if brk_ov is not None:
        ctx.log.entry("break-override", page=blk["page"], block=blk["rk"],
                      breaks=brk_ov.get("breaks"), text=text[:60])
        if brk_ov.get("breaks") and rich.get("lineJoins"):
            node["breaks"] = rich["lineJoins"]
        return node
    if _hard_returns(blk) and rich.get("lineJoins"):
        node["breaks"] = rich["lineJoins"]
        ctx.log.entry("hard-returns", page=blk["page"], block=blk["rk"],
                      lines=len(blk["lines"]),
                      reason="2+ interior lines end with terminal punctuation")
        _question(ctx, "hard-returns", node,
                  f"“{text[:60]}…” looks like intentional one-per-line text "
                  "(credits, addresses). Keep the line breaks, or flow it as "
                  "one paragraph?",
                  ["line breaks", "flowing paragraph"], "line breaks")
    return node


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
    return short >= 2 and item_starts >= 2 and item_starts >= 0.6 * len(interior)


def _figure_node(ctx, reg, pages, fig_count):
    page = pages[reg["page"]]
    src, w_px, h_px = _crop(ctx, reg, page, fig_count)
    caption = reg.get("caption")
    rk = ctx.log.entry("figure-crop", page=reg["page"], src=src,
                       bbox=[round(v, 1) for v in reg["bbox"]],
                       region=reg["rk"], caption=(caption or "")[:80])
    node = {"type": "figure", "src": src,
            "width": round(reg["bbox"][2] - reg["bbox"][0]),
            "height": round(reg["bbox"][3] - reg["bbox"][1]),
            "alt": caption or f"Figure from page {reg['page']}",
            "page": reg["page"], "bbox": reg["bbox"], "rk": rk,
            "data": {"region": reg["rk"]}}
    node["nid"] = _stable_id("n", ctx.nids, "figure", node["page"], node["bbox"])
    if caption:
        node["caption"] = caption
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


def _try_table(ctx, reg, blocks, texts, pages):
    """A boxed region whose grid is literally drawn (ruled lines) and whose
    blocks cluster into columns is a table, not a callout."""
    idx = reg["blockIdx"]
    if len(idx) < 4 or reg.get("endPage"):
        return None
    page = pages[reg["page"]]
    l0, b0, r0, t0 = reg["bbox"]
    hl = vl = 0
    for o in page.get("objects", []):
        if o[0] != OBJ_PATH:
            continue
        l, b, r, t = o[1:5]
        if l < l0 - 5 or r > r0 + 5 or b < b0 - 5 or t > t0 + 5:
            continue
        if t - b < 3 and r - l > 30:
            hl += 1
        elif r - l < 3 and t - b > 10:
            vl += 1
    if hl < 3 or vl < 2:
        return None

    # columns by block center-x
    by_cx = sorted(idx, key=lambda i: (blocks[i]["bbox"][0] + blocks[i]["bbox"][2]) / 2)
    col_of = {}
    col = -1
    prev_cx = None
    for i in by_cx:
        cx = (blocks[i]["bbox"][0] + blocks[i]["bbox"][2]) / 2
        if prev_cx is None or cx - prev_cx > 50:
            col += 1
        col_of[i] = col
        prev_cx = cx
    n_cols = col + 1
    if n_cols < 2:
        return None

    # rows by vertical-interval grouping (top-down)
    rows_idx = []
    for i in sorted(idx, key=lambda i: -blocks[i]["bbox"][3]):
        b, t = blocks[i]["bbox"][1], blocks[i]["bbox"][3]
        if rows_idx and t > rows_idx[-1]["min_b"]:
            rows_idx[-1]["cells"].append(i)
            rows_idx[-1]["min_b"] = min(rows_idx[-1]["min_b"], b)
        else:
            rows_idx.append({"cells": [i], "min_b": b})

    rows = []
    for row in rows_idx:
        cells = [""] * n_cols
        for i in row["cells"]:
            c = col_of[i]
            cells[c] = (cells[c] + " " + texts[i]).strip()
        rows.append(cells)
    if len(rows) < 2:
        return None

    header = all(c.strip() for c in rows[0])
    rk = ctx.log.entry("table", page=reg["page"], bbox=[round(v, 1) for v in reg["bbox"]],
                       cols=n_cols, rows=len(rows), header=header,
                       hlines=hl, vlines=vl, region=reg["rk"])
    node = {"type": "table", "rows": rows, "header": header,
            "page": reg["page"], "bbox": reg["bbox"], "rk": rk,
            "data": {"region": reg["rk"]}}
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

def _column_split(bboxes):
    """x of the gutter when the page is laid out in two columns, else None.
    Requires two well-populated x-clusters of narrow blocks with a clear gap
    that no narrow block straddles."""
    if len(bboxes) < 5:
        return None
    l0 = min(b[0] for b in bboxes)
    r0 = max(b[2] for b in bboxes)
    width = max(r0 - l0, 1.0)
    narrow = [b for b in bboxes if (b[2] - b[0]) <= 0.6 * width]
    if len(narrow) < 4:
        return None
    centers = sorted((b[0] + b[2]) / 2 for b in narrow)
    best_gap, split0 = 0.0, None
    for a, b in zip(centers, centers[1:]):
        if b - a > best_gap:
            best_gap, split0 = b - a, (a + b) / 2
    if split0 is None or best_gap < 0.18 * width:
        return None
    left = [b for b in narrow if (b[0] + b[2]) / 2 < split0]
    right = [b for b in narrow if (b[0] + b[2]) / 2 >= split0]
    if len(left) < 2 or len(right) < 2:
        return None
    # real columns have an empty gutter between the groups' edges
    gutter_l = max(b[2] for b in left)
    gutter_r = min(b[0] for b in right)
    if gutter_r - gutter_l < 6:
        return None
    return (gutter_l + gutter_r) / 2


def _flow_order(items, bboxes, split):
    """Reading order for a two-column page: top-down, with full-width
    elements acting as band separators; within a band, the left column reads
    fully before the right."""
    l0 = min(b[0] for b in bboxes)
    r0 = max(b[2] for b in bboxes)
    width = max(r0 - l0, 1.0)
    order = sorted(range(len(items)), key=lambda k: -bboxes[k][3])
    out = []
    band = []

    def flush():
        if not band:
            return
        left = [k for k in band if (bboxes[k][0] + bboxes[k][2]) / 2 < split]
        right = [k for k in band if k not in left]
        out.extend(sorted(left, key=lambda k: -bboxes[k][3]))
        out.extend(sorted(right, key=lambda k: -bboxes[k][3]))
        band.clear()

    for k in order:
        if (bboxes[k][2] - bboxes[k][0]) > 0.6 * width:
            flush()
            out.append(k)
        else:
            band.append(k)
    flush()
    return [items[k] for k in out]


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
            items = [re.sub(f"^[{re.escape(BULLETS)}]\\s*", "", n["text"]).strip()
                     for n in run]
            bbox = [min(n["bbox"][0] for n in run), min(n["bbox"][1] for n in run),
                    max(n["bbox"][2] for n in run), max(n["bbox"][3] for n in run)]
            page = run[0]["page"]
            rk = ctx.log.entry("list", page=page, bbox=bbox, items=len(items),
                               reason="struct tags LBody/LI",
                               merged=[n["rk"] for n in run])
            for n in run:
                if n["page"] != page:  # grouped across pages: credit source
                    ctx.audit_moved[n["page"]] += _alnum(n["text"])
            data = {"role": "L"}
            if last_lbl[0]:
                data["marker"] = last_lbl[0]
            out.append({"type": "list", "items": items, "page": page,
                        "bbox": bbox, "rk": rk, "data": data,
                        "nid": _stable_id("n", ctx.nids, "list", page, bbox,
                                          " ".join(items))})
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
        if len(run) >= 2:
            items = [re.sub(f"^[{re.escape(BULLETS)}]\\s*", "", n["text"]).strip()
                     for n in run]
            bbox = [min(n["bbox"][0] for n in run), min(n["bbox"][1] for n in run),
                    max(n["bbox"][2] for n in run), max(n["bbox"][3] for n in run)]
            page = run[0]["page"]
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
                                          " ".join(items))})
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
                run.append({"text": cand["text"][cm[2]:].strip(),
                            "node": cand})
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
                        sub["items"].append(s["text"][sm[2]:].strip())
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
            items = [({"text": r["text"], "sub": r["sub"]} if r.get("sub")
                      else r["text"]) for r in run]
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


def _aside_layout_and_pullquotes(ctx, nodes):
    """Two post-passes over the assembled flow:
    - asides narrower than the text column get layout provenance (width
      fraction + anchored side) so layer 3 can float them like the original;
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
        if n["type"] != "aside":
            out.append(n)
            continue
        w = n["bbox"][2] - n["bbox"][0]
        frac = w / col_w
        if frac <= 0.7:
            anchor = None
            if col_r - n["bbox"][2] < 0.08 * col_w and \
                    n["bbox"][0] - col_l > 0.2 * col_w:
                anchor = "right"
            elif n["bbox"][0] - col_l < 0.08 * col_w and \
                    col_r - n["bbox"][2] > 0.2 * col_w:
                anchor = "left"
            if anchor:
                n["layout"] = {"widthFrac": round(frac, 3), "anchor": anchor}
                ctx.log.entry("aside-layout", page=n["page"], nid=n["nid"],
                              widthFrac=n["layout"]["widthFrac"], anchor=anchor)

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
            for key in ("refs", "links"):
                if ch.get(key):
                    prev.setdefault(key, []).extend(
                        [r[0] + off, r[1] + off, *r[2:]] for r in ch[key])
            ctx.log.entry("join-pagebreak", page=ch["page"], into=prev["rk"],
                          joined=ch["text"][:60])
            continue
        out.append(ch)
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


def _looks_like_heading(text):
    text = text.strip()
    if re.fullmatch(r"[\$€£]?[\d,.\s]+%?", text):
        return False  # numeric/currency labels are not headings
    return (0 < len(text) <= 200
            and not text.endswith((".", ",", ";", ":", "…"))
            and re.search(r"[A-Za-z0-9]{2}", text) is not None)


def _is_bullet_list(blk):
    """Bullet items wrap: the block is a list when it opens with a bullet and
    has at least two bulleted lines; unbulleted lines are continuations."""
    starts = [l["text"][:1] in BULLETS for l in blk["lines"]]
    return len(starts) >= 2 and starts[0] and sum(starts) >= 2


def _item_texts(items):
    for it in items:
        if isinstance(it, str):
            yield it
        else:
            yield it.get("text", "")
            sub = it.get("sub")
            if sub:
                yield from sub.get("items", [])


def _ordinal_block(blk):
    """A block whose lines carry sequential ordinal markers (any start, for
    resumed numbering: <ol start>). Deeper-indented alpha lines under a
    numeric item nest one level. Returns (style, start, items) or None."""
    lines = blk["lines"]
    first = _ol_marker(lines[0]["text"])
    if first is None or len(lines) < 2:
        return None
    style0, start, off0 = first
    base_x = lines[0]["bbox"][0]
    items = [{"text": lines[0]["text"][off0:].strip()}]
    expected = start + 1
    marked = 1
    for l in lines[1:]:
        m = _ol_marker(l["text"])
        if m and m[0] == style0 and m[1] == expected:
            items.append({"text": l["text"][m[2]:].strip()})
            expected += 1
            marked += 1
        elif m and m[0] != style0 and l["bbox"][0] > base_x + 6:
            sub = items[-1].setdefault(
                "sub", {"ordered": m[0], "start": m[1], "items": []})
            sub["items"].append(l["text"][m[2]:].strip())
            marked += 1
        elif items[-1].get("sub"):
            items[-1]["sub"]["items"][-1] += " " + l["text"]
        else:
            items[-1]["text"] += " " + l["text"]
    if marked < 2:
        return None
    if not any(it.get("sub") for it in items):
        items = [it["text"] for it in items]
    return style0, start, items


def _bullet_items(blk):
    items = []
    for l in blk["lines"]:
        if l["text"][:1] in BULLETS:
            items.append(re.sub(f"^[{re.escape(BULLETS)}]\\s*", "", l["text"]).strip())
        elif items:
            items[-1] += " " + l["text"]
    return items


def _join_block(ctx, blk, link_colors=()):
    """Join a block's lines into flowing text, dehyphenating soft wraps and
    carrying per-line superscript/link char ranges into the joined offsets.
    Text colored like the document's annotated links but lacking an annotation
    becomes a styled-link range (print PDFs often style cross-references as
    links without targets).
    Returns {"text", "sups": [[s,e]], "links": [[s,e,target]]}."""
    out = ""
    sups, links, emph = [], [], []
    line_joins = []  # offsets of the spaces where source lines were joined
    for l in blk["lines"]:
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

        line_font = ctx.fonts[l["fontIdx"]]
        for s, e, fi in l.get("fontRuns", []):
            f = ctx.fonts[fi]
            kind = _font_emphasis(f["name"], f.get("weight", 0),
                                  line_font["name"])
            if kind and (e - s) < 0.9 * max(len(t), 1):  # sub-line runs only
                emph.append([s + base, e + base, kind])

        styled = []
        if l["colorIdx"] in link_colors:
            styled.append([base, base + len(t)])
        else:
            styled.extend([s + base, e + base] for s, e, col in l.get("colors", [])
                          if col in link_colors)
        for s, e in styled:
            if not any(s < re_ and rs < e for rs, re_, _t in real):
                links.append([s, e, {"styled": True}])
    # merge adjacent same-kind emphasis (a phrase wrapped across lines)
    merged_emph = []
    for s, e, kind in sorted(emph):
        if merged_emph and s - merged_emph[-1][1] <= 1 \
                and merged_emph[-1][2] == kind:
            merged_emph[-1][1] = e
        else:
            merged_emph.append([s, e, kind])
    return {"text": out, "sups": sups, "links": links,
            "emph": merged_emph, "lineJoins": line_joins}


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
        for l, b, r, t, role in regs:
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


def _toc_pages(ctx, pages, blocks):
    """Pages that are a table of contents: many dot-leader lines, or a
    'Contents' title plus several lines ending in page numbers. The TOC is
    dropped entirely; navigation is reconstructed from our heading tree."""
    toc = set()
    for p in pages.values():
        lines = [l["text"] for blk in blocks if blk["page"] == p["n"]
                 for l in blk["lines"]]
        leader = sum(1 for t in lines if re.search(r"\.{3,}\s*\d{1,3}$", t))
        trailing = sum(1 for t in lines if re.search(r"\s\d{1,3}$", t))
        titled = any(re.fullmatch(r"(table of )?contents", t.strip(), re.I)
                     for t in lines)
        if leader >= 5 or (titled and trailing >= 3):
            toc.add(p["n"])
            ctx.log.entry("toc-page", page=p["n"], leader_lines=leader,
                          trailing_num_lines=trailing, titled=titled)
    return toc


NOTE_START = re.compile(r"^(\d{1,3})(?:[.)]\s*|\s+)(?=\S)")


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
    return None
NOTES_HEADING = re.compile(r"(end\s*)?notes?|references|sources", re.I)


def _find_notes(ctx, pages, blocks, texts, skip, body_size):
    """Footnote/endnote text in either form: numbered blocks following a
    notes-section heading, or small numbered text at the bottom of a page.
    Returns (notes, absorbed block indexes, sectioned flag)."""
    notes, note_idx = [], set()
    in_section = False
    sectioned = False
    expected = None  # next anticipated note number; gates against wrapped DOIs
    for i, (blk, text) in enumerate(zip(blocks, texts)):
        if i in skip:
            continue
        size = _dominant_size(blk)
        if NOTES_HEADING.fullmatch(text.strip()):
            # a notes-ish section label (Endnotes, Sources, References) at any
            # size starts a fresh section — and must never be eaten as a
            # continuation of the previous section's last note
            in_section = True
            expected = None
            continue
        marker = _line_marker(blk["lines"][0])
        if in_section:
            if size > body_size * 1.15:
                in_section = False  # next heading ends the notes section
            elif marker:
                new, lead, expected = _parse_notes(ctx, blk, expected)
                if lead and notes:
                    notes[-1]["text"] += " " + lead
                notes.extend(new)
                if new or (lead and notes):
                    note_idx.add(i)
                    sectioned = True
                continue
            elif notes and size <= body_size * 1.05 and text[:1].islower():
                # continuation = a wrap of the previous note (starts
                # mid-sentence); anything else ends the section instead of
                # being silently appended to the last note
                notes[-1]["text"] += " " + text
                note_idx.add(i)
                continue
            else:
                in_section = False
        if not in_section and marker and size <= 0.92 * body_size:
            page = pages[blk["page"]]
            # bottom of the page, or anywhere when the marker is a leading
            # superscript (unambiguous footnote form, e.g. roman markers on
            # the last page)
            if blk["bbox"][1] < 0.18 * page["height"] or marker[3]:
                new, lead, expected = _parse_notes(ctx, blk, expected)
                if lead and notes:
                    notes[-1]["text"] += " " + lead
                notes.extend(new)
                if new or (lead and notes):
                    note_idx.add(i)
    notes.sort(key=lambda n: n["n"])
    return notes, note_idx, sectioned


def _parse_notes(ctx, blk, expected):
    """Split a block into individual numbered notes (one block often holds
    several notes as consecutive lines). Note numbers are sequential, so a
    numbered-looking line that doesn't continue the sequence (a wrapped DOI
    like "10.1073/...") is a continuation, not a new note.
    Returns (notes, leading continuation text, next expected number)."""
    notes = []
    leading = []
    for l in blk["lines"]:
        marker = _line_marker(l)
        if marker and (expected is None or marker[0] == expected):
            num, raw, off, _is_sup = marker
            rk = ctx.log.entry("note", page=blk["page"], n=num, marker=raw,
                               block=blk["rk"], text=l["text"][:80])
            notes.append({"n": num, "marker": raw, "page": blk["page"],
                          "text": l["text"][off:].lstrip(".) ").strip(), "rk": rk})
            expected = num + 1
        else:
            if marker:
                ctx.log.entry("note-continuation", page=blk["page"],
                              rejected_n=marker[0], expected=expected,
                              text=l["text"][:60])
            if notes:
                notes[-1]["text"] += " " + l["text"]
            else:
                leading.append(l["text"])
    return notes, " ".join(leading), expected


def _heading_id(text, used):
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "section"
    hid, i = base, 1
    while hid in used:
        i += 1
        hid = f"{base}-{i}"
    used.add(hid)
    return hid
