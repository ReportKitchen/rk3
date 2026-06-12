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

VERSION = 13

BULLETS = "•◦▪‣–—-*·"
OBJ_PATH, OBJ_IMAGE, OBJ_SHADING = 2, 3, 4
# objects: [type, l, b, r, t, fillIdx, strokeIdx, filled, stroked]
OT, OL, OB, OR_, OTOP = range(5)


def _stable_id(prefix, used, kind, page, bbox):
    raw = f"{kind}|{page}|{round(bbox[0])},{round(bbox[1])},{round(bbox[2])},{round(bbox[3])}"
    base = prefix + hashlib.sha1(raw.encode()).hexdigest()[:10]
    sid, i = base, 1
    while sid in used:
        i += 1
        sid = f"{base}-{i}"
    used.add(sid)
    return sid


def run(ctx):
    asm = ctx.artifact("assemble")
    blocks, fonts = asm["blocks"], asm["fonts"]
    pages = {p["n"]: p for p in asm["pages"]}
    ctx.questions = []
    ctx.nids = set()
    ctx.qids = set()

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
    for i, blk in enumerate(blocks):
        if i in skip:
            continue
        role, cov = roles[i]
        if role == "Artifact" and cov > 0.5:
            skip.add(i)
            ctx.log.entry("strip-artifact", page=blk["page"], block=blk["rk"],
                          coverage=round(cov, 2), text=texts[i][:60])
        elif drop_toc and role in ("TOC", "TOCI") and cov > 0.5:
            skip.add(i)
            ctx.log.entry("toc-tag-drop", page=blk["page"], block=blk["rk"],
                          text=texts[i][:60])

    regions = _detect_regions(ctx, pages, blocks, texts, body_size, toc_pages)
    regions = _merge_cross_page_callouts(ctx, regions, pages)
    absorbed = {}  # block index -> region
    for reg in regions:
        for bi in reg["blockIdx"]:
            absorbed[bi] = reg
    _find_captions(ctx, regions, blocks, texts, absorbed, body_size, roles)
    absorbed.update(dict.fromkeys(skip))

    notes, note_idx = _find_notes(ctx, pages, blocks, texts, absorbed, body_size)
    absorbed.update(dict.fromkeys(note_idx))

    main_idx = [i for i in range(len(blocks)) if i not in absorbed]
    levels = _heading_levels(ctx, [blocks[i] for i in main_idx],
                             [texts[i] for i in main_idx], body_size)

    # weave figure/callout regions into the block flow by vertical position
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

    nodes = []
    used_ids = set()
    fig_count = 0
    for page_n in sorted(page_items):
        for kind, ref in page_items[page_n]:
            if kind == "block":
                nodes.append(_block_node(ctx, blocks[ref], rich[ref], fonts,
                                         levels, body_size, used_ids,
                                         role=roles[ref], tag_levels=tag_levels))
            else:
                if ref["kind"] == "figure":
                    fig_count += 1
                    node = _figure_node(ctx, ref, pages, fig_count)
                else:
                    node = _aside_node(ctx, ref, blocks, rich, fonts, body_size)
                nodes.append(node)
                if ref.get("uncertain"):
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

    # sentences interrupted by page breaks happen in the main flow too,
    # not just inside callouts
    nodes = _join_pagebreak_sentences(ctx, nodes)

    if notes:
        last = blocks[max(note_idx)]
        rk = ctx.log.entry("footnotes", count=len(notes),
                           numbers=[n["n"] for n in notes][:20])
        node = {"type": "footnotes", "notes": notes, "page": last["page"],
                "bbox": last["bbox"], "rk": rk, "data": {}}
        node["nid"] = _stable_id("n", ctx.nids, "footnotes", node["page"], node["bbox"])
        nodes.append(node)

    title = next((n["text"] for n in nodes if n["type"] == "heading" and n["level"] == 1),
                 ctx.source.stem)
    ctx.write_artifact("analyze", {
        "title": title,
        "pages": {str(p["n"]): [p["width"], p["height"]] for p in asm["pages"]},
        "questions": ctx.questions,
        "body": nodes,
    })


def _question(ctx, kind, node, prompt, options, chosen):
    qid = _stable_id("q", ctx.qids, kind, node["page"], node["bbox"])
    ctx.questions.append({"qid": qid, "nid": node["nid"], "page": node["page"],
                          "kind": kind, "prompt": prompt, "options": options,
                          "chosen": chosen})
    ctx.log.entry("question", qid=qid, nid=node["nid"], kind=kind,
                  chosen=chosen, prompt=prompt)


# ---------------------------------------------------------------- regions ---

def _detect_regions(ctx, pages, blocks, texts, body_size, toc_pages=()):
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
            reg = _classify_cluster(ctx, page, cluster, blocks, texts, body_size)
            if reg:
                regions.append(reg)
    return regions


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


def _classify_cluster(ctx, page, cluster, blocks, texts, body_size):
    bbox = cluster["bbox"]
    w, h = page["width"], page["height"]
    if (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) > 0.9 * w * h:
        return None
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

    uncertain = False
    if graphic and (n_images >= 1 or chars_inside <= 400):
        kind = "figure"
        # text-heavy vector region: the figure/callout call is genuinely close
        uncertain = n_images == 0 and chars_inside > 150
    elif (graphic or boxed) and inside:
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
            "uncertain": uncertain, "blockIdx": absorbed_idx}


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

def _block_node(ctx, blk, rich, fonts, levels, body_size, used_ids,
                in_aside=False, role=(None, 0.0), tag_levels=None):
    text = rich["text"]
    size = _dominant_size(blk)
    font = fonts[blk["lines"][0]["fontIdx"]]
    prov = {"font": font["name"], "weight": font["weight"], "size": size}
    tag_role, tag_cov = role
    if tag_role:
        prov["role"] = tag_role

    if not in_aside and tag_levels and tag_role in tag_levels and tag_cov > 0.5 \
            and text.strip():
        level = tag_levels[tag_role]
        hid = _heading_id(text, used_ids)
        rk = ctx.log.entry("heading", level=level, page=blk["page"],
                           bbox=blk["bbox"], size=size, body_size=body_size,
                           reason=f"struct tag {tag_role} (coverage {tag_cov:.2f})",
                           text=text[:120], block=blk["rk"])
        return {"type": "heading", "level": level, "text": text, "id": hid,
                "page": blk["page"], "bbox": blk["bbox"], "rk": rk, "data": prov,
                "nid": _stable_id("n", ctx.nids, "heading", blk["page"], blk["bbox"])}

    if not in_aside and size in levels and _looks_like_heading(text):
        level = levels[size]
        hid = _heading_id(text, used_ids)
        # authors tag genuine headings as P often enough that a P tag must
        # not veto strong size evidence — but the disagreement is exactly
        # what the question system is for
        conflict = bool(tag_levels) and tag_role == "P" and tag_cov > 0.5
        reason = f"size {size} ranked #{level} above body {body_size}"
        if conflict:
            reason += " (struct tag says P — kept as heading, question emitted)"
        rk = ctx.log.entry("heading", level=level, page=blk["page"],
                           bbox=blk["bbox"], size=size, body_size=body_size,
                           reason=reason, text=text[:120], block=blk["rk"])
        node = {"type": "heading", "level": level, "text": text, "id": hid,
                "page": blk["page"], "bbox": blk["bbox"], "rk": rk, "data": prov}
        node["nid"] = _stable_id("n", ctx.nids, "heading", node["page"], node["bbox"])
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

    if _is_bullet_list(blk):
        items = [re.sub(f"^[{re.escape(BULLETS)}]\\s*", "", l["text"]).strip()
                 for l in blk["lines"]]
        rk = ctx.log.entry("list", page=blk["page"], bbox=blk["bbox"],
                           items=len(items), reason="every line starts with a bullet char",
                           block=blk["rk"])
        node = {"type": "list", "items": items, "page": blk["page"],
                "bbox": blk["bbox"], "rk": rk, "data": prov}
        node["nid"] = _stable_id("n", ctx.nids, "list", node["page"], node["bbox"])
        return node

    strong = in_aside and size > 1.15 * body_size
    refs = [[s, e, int(text[s:e])] for s, e in rich.get("sups", [])
            if text[s:e].isdigit() and len(text[s:e]) <= 3]
    rk = ctx.log.entry("paragraph", page=blk["page"], bbox=blk["bbox"],
                       size=size, strong=strong, refs=[r[2] for r in refs],
                       links=len(rich.get("links", [])),
                       text=text[:120], block=blk["rk"])
    node = {"type": "paragraph", "text": text, "page": blk["page"],
            "bbox": blk["bbox"], "rk": rk, "data": prov}
    node["nid"] = _stable_id("n", ctx.nids, "paragraph", node["page"], node["bbox"])
    if strong:
        node["strong"] = True
    if refs:
        node["refs"] = refs
    if rich.get("links"):
        node["links"] = rich["links"]
    return node


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


def _aside_node(ctx, reg, blocks, rich, fonts, body_size):
    # callout boxes are single-column: order children top-down by position
    # (page first, for boxes merged across a page break) so the headline
    # leads regardless of content-stream order
    ordered = sorted(reg["blockIdx"],
                     key=lambda i: (blocks[i]["page"], -blocks[i]["bbox"][3]))
    children = [_block_node(ctx, blocks[i], rich[i], fonts, {}, body_size,
                            set(), in_aside=True)
                for i in ordered]
    children = _join_pagebreak_sentences(ctx, children)
    rk = ctx.log.entry("aside", page=reg["page"],
                       bbox=[round(v, 1) for v in reg["bbox"]],
                       end_page=reg.get("endPage"),
                       region=reg["rk"], children=len(children))
    node = {"type": "aside", "children": children, "page": reg["page"],
            "bbox": reg["bbox"], "rk": rk, "data": {"region": reg["rk"]}}
    node["nid"] = _stable_id("n", ctx.nids, "aside", node["page"], node["bbox"])
    return node


# -------------------------------------------------------------- text utils ---

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


def _looks_like_heading(text):
    text = text.strip()
    if re.fullmatch(r"[\$€£]?[\d,.\s]+%?", text):
        return False  # numeric/currency labels are not headings
    return (0 < len(text) <= 200
            and not text.endswith((".", ",", ";", ":", "…"))
            and re.search(r"[A-Za-z0-9]{2}", text) is not None)


def _is_bullet_list(blk):
    return len(blk["lines"]) >= 2 and all(
        l["text"][:1] in BULLETS for l in blk["lines"])


def _join_block(ctx, blk, link_colors=()):
    """Join a block's lines into flowing text, dehyphenating soft wraps and
    carrying per-line superscript/link char ranges into the joined offsets.
    Text colored like the document's annotated links but lacking an annotation
    becomes a styled-link range (print PDFs often style cross-references as
    links without targets).
    Returns {"text", "sups": [[s,e]], "links": [[s,e,target]]}."""
    out = ""
    sups, links = [], []
    for l in blk["lines"]:
        t = l["text"]
        if out.endswith("-") and t[:1].islower():
            ctx.log.entry("dehyphenate", page=blk["page"],
                          joined=out[-12:] + "|" + t[:12], block=blk["rk"])
            base = len(out) - 1
            out = out[:-1] + t
        elif out:
            base = len(out) + 1
            out += " " + t
        else:
            base = 0
            out = t
        real = [[s + base, e + base, target]
                for s, e, target in l.get("links", [])]
        links.extend(real)
        sups.extend([s + base, e + base] for s, e in l.get("sups", []))

        styled = []
        if l["colorIdx"] in link_colors:
            styled.append([base, base + len(t)])
        else:
            styled.extend([s + base, e + base] for s, e, col in l.get("colors", [])
                          if col in link_colors)
        for s, e in styled:
            if not any(s < re_ and rs < e for rs, re_, _t in real):
                links.append([s, e, {"styled": True}])
    return {"text": out, "sups": sups, "links": links}


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
NOTES_HEADING = re.compile(r"(end\s*)?notes?|references|sources", re.I)


def _find_notes(ctx, pages, blocks, texts, skip, body_size):
    """Footnote/endnote text in either form: numbered blocks following a
    notes-section heading, or small numbered text at the bottom of a page.
    Returns (notes [{n, text, rk}], set of absorbed block indexes)."""
    notes, note_idx = [], set()
    in_section = False
    expected = None  # next anticipated note number; gates against wrapped DOIs
    for i, (blk, text) in enumerate(zip(blocks, texts)):
        if i in skip:
            continue
        size = _dominant_size(blk)
        if NOTES_HEADING.fullmatch(text.strip()) and size > body_size * 1.15:
            in_section = True
            continue
        starts_num = NOTE_START.match(text)
        if in_section:
            if size > body_size * 1.15:
                in_section = False  # next heading ends the notes section
            elif starts_num:
                new, lead, expected = _parse_notes(ctx, blk, expected)
                if lead and notes:
                    notes[-1]["text"] += " " + lead
                notes.extend(new)
                if new or (lead and notes):
                    note_idx.add(i)
                continue
            elif notes and size <= body_size * 1.05:
                notes[-1]["text"] += " " + text  # continuation block
                note_idx.add(i)
                continue
        if not in_section and starts_num and size <= 0.92 * body_size:
            page = pages[blk["page"]]
            if blk["bbox"][1] < 0.18 * page["height"]:
                new, lead, expected = _parse_notes(ctx, blk, expected)
                if lead and notes:
                    notes[-1]["text"] += " " + lead
                notes.extend(new)
                if new or (lead and notes):
                    note_idx.add(i)
    notes.sort(key=lambda n: n["n"])
    return notes, note_idx


def _parse_notes(ctx, blk, expected):
    """Split a block into individual numbered notes (one block often holds
    several notes as consecutive lines). Note numbers are sequential, so a
    numbered-looking line that doesn't continue the sequence (a wrapped DOI
    like "10.1073/...") is a continuation, not a new note.
    Returns (notes, leading continuation text, next expected number)."""
    notes = []
    leading = []
    for l in blk["lines"]:
        m = NOTE_START.match(l["text"])
        num = int(m.group(1)) if m else None
        if m and (expected is None or num == expected):
            rk = ctx.log.entry("note", page=blk["page"], n=num,
                               block=blk["rk"], text=l["text"][:80])
            notes.append({"n": num, "text": l["text"][m.end():].strip(), "rk": rk})
            expected = num + 1
        else:
            if m:
                ctx.log.entry("note-continuation", page=blk["page"],
                              rejected_n=num, expected=expected,
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
