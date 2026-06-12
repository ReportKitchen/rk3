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
  every node: { "page", "bbox", "rk", "data": {provenance} }
"""

import re
from collections import Counter

from PIL import Image

VERSION = 4

BULLETS = "•◦▪‣–—-*·"
OBJ_PATH, OBJ_IMAGE, OBJ_SHADING = 2, 3, 4
# objects: [type, l, b, r, t, fillIdx, strokeIdx, filled, stroked]
OT, OL, OB, OR_, OTOP = range(5)


def run(ctx):
    asm = ctx.artifact("assemble")
    blocks, fonts = asm["blocks"], asm["fonts"]
    pages = {p["n"]: p for p in asm["pages"]}

    texts = [_join_lines(ctx, blk) for blk in blocks]
    body_size = _body_size(ctx, blocks)

    regions = _detect_regions(ctx, pages, blocks, texts, body_size)
    absorbed = {}  # block index -> region
    for reg in regions:
        for bi in reg["blockIdx"]:
            absorbed[bi] = reg
    _find_captions(ctx, regions, blocks, texts, absorbed, body_size)

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
                nodes.append(_block_node(ctx, blocks[ref], texts[ref], fonts,
                                         levels, body_size, used_ids))
            elif ref["kind"] == "figure":
                fig_count += 1
                nodes.append(_figure_node(ctx, ref, pages, fig_count))
            else:
                nodes.append(_aside_node(ctx, ref, blocks, texts, fonts, body_size))

    title = next((n["text"] for n in nodes if n["type"] == "heading" and n["level"] == 1),
                 ctx.source.stem)
    ctx.write_artifact("analyze", {
        "title": title,
        "pages": {str(p["n"]): [p["width"], p["height"]] for p in asm["pages"]},
        "body": nodes,
    })


# ---------------------------------------------------------------- regions ---

def _detect_regions(ctx, pages, blocks, texts, body_size):
    """Cluster graphic objects per page, classify clusters as figure/callout."""
    repeated = _repeated_images(pages)
    regions = []
    for page in pages.values():
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

    if graphic and (n_images >= 1 or chars_inside <= 400):
        kind = "figure"
    elif (graphic or boxed) and inside:
        kind = "callout"
    else:
        return None

    rk = ctx.log.entry(kind, page=page["n"], bbox=[round(v, 1) for v in bbox],
                       images=n_images, paths=n_paths, shadings=n_shade,
                       text_blocks=len(inside), chars_inside=chars_inside,
                       kept_big_text=[texts[i][:40] for i in big_inside],
                       reason=f"images={n_images} shadings={n_shade} paths={n_paths} "
                              f"chars_inside={chars_inside}")
    return {"kind": kind, "page": page["n"], "bbox": bbox, "rk": rk,
            "blockIdx": inside if kind == "figure" else sorted(inside)}


def _find_captions(ctx, regions, blocks, texts, absorbed, body_size):
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
            captionish = (re.match(r"(figure|fig\.|table|chart|exhibit|source[:.])",
                                   text, re.I)
                          or _dominant_size(blk) < 0.95 * body_size)
            if captionish and len(text) < 500:
                reg["caption"] = text
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

def _block_node(ctx, blk, text, fonts, levels, body_size, used_ids, in_aside=False):
    size = _dominant_size(blk)
    font = fonts[blk["lines"][0]["fontIdx"]]
    prov = {"font": font["name"], "weight": font["weight"], "size": size}

    if not in_aside and size in levels and _looks_like_heading(text):
        level = levels[size]
        hid = _heading_id(text, used_ids)
        rk = ctx.log.entry("heading", level=level, page=blk["page"],
                           bbox=blk["bbox"], size=size, body_size=body_size,
                           reason=f"size {size} ranked #{level} above body {body_size}",
                           text=text[:120], block=blk["rk"])
        return {"type": "heading", "level": level, "text": text, "id": hid,
                "page": blk["page"], "bbox": blk["bbox"], "rk": rk, "data": prov}

    if _is_bullet_list(blk):
        items = [re.sub(f"^[{re.escape(BULLETS)}]\\s*", "", l["text"]).strip()
                 for l in blk["lines"]]
        rk = ctx.log.entry("list", page=blk["page"], bbox=blk["bbox"],
                           items=len(items), reason="every line starts with a bullet char",
                           block=blk["rk"])
        return {"type": "list", "items": items, "page": blk["page"],
                "bbox": blk["bbox"], "rk": rk, "data": prov}

    strong = in_aside and size > 1.15 * body_size
    rk = ctx.log.entry("paragraph", page=blk["page"], bbox=blk["bbox"],
                       size=size, strong=strong, text=text[:120], block=blk["rk"])
    node = {"type": "paragraph", "text": text, "page": blk["page"],
            "bbox": blk["bbox"], "rk": rk, "data": prov}
    if strong:
        node["strong"] = True
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


def _aside_node(ctx, reg, blocks, texts, fonts, body_size):
    children = [_block_node(ctx, blocks[i], texts[i], fonts, {}, body_size,
                            set(), in_aside=True)
                for i in reg["blockIdx"]]
    rk = ctx.log.entry("aside", page=reg["page"],
                       bbox=[round(v, 1) for v in reg["bbox"]],
                       region=reg["rk"], children=len(children))
    return {"type": "aside", "children": children, "page": reg["page"],
            "bbox": reg["bbox"], "rk": rk, "data": {"region": reg["rk"]}}


# -------------------------------------------------------------- text utils ---

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


def _join_lines(ctx, blk):
    """Join a block's lines into flowing text, dehyphenating soft wraps."""
    out = ""
    for l in blk["lines"]:
        t = l["text"]
        if out.endswith("-") and t[:1].islower():
            ctx.log.entry("dehyphenate", page=blk["page"],
                          joined=out[-12:] + "|" + t[:12], block=blk["rk"])
            out = out[:-1] + t
        elif out:
            out += " " + t
        else:
            out = t
    return out.strip()


def _heading_id(text, used):
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "section"
    hid, i = base, 1
    while hid in used:
        i += 1
        hid = f"{base}-{i}"
    used.add(hid)
    return hid
