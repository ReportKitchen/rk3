"""Analyze stage: classify blocks into document structure and emit the IR.

v1 scope: heading levels (font-size clustering, normalized to h1..h6),
paragraphs (with dehyphenation), simple bulleted lists. Figures, callouts,
tables, and footnotes land in later milestones.

Artifact: ir.json
  { "title", "body": [ node... ] }
  node: { "type": "heading"|"paragraph"|"list",
          "level"?, "text"?, "items"?, "id"?,
          "page", "bbox", "rk", "data": { font/size provenance } }
"""

import re
from collections import Counter

VERSION = 1

BULLETS = "•◦▪‣–—-*·"


def run(ctx):
    asm = ctx.artifact("assemble")
    blocks, fonts = asm["blocks"], asm["fonts"]

    body_size = _body_size(ctx, blocks)
    levels = _heading_levels(ctx, blocks, body_size)

    nodes = []
    used_ids = set()
    for blk in blocks:
        size = _dominant_size(blk)
        font = fonts[blk["lines"][0]["fontIdx"]]
        prov = {"font": font["name"], "weight": font["weight"], "size": size}
        text = _join_lines(ctx, blk)

        if size in levels and _looks_like_heading(text):
            level = levels[size]
            hid = _heading_id(text, used_ids)
            rk = ctx.log.entry("heading", level=level, page=blk["page"],
                               bbox=blk["bbox"], size=size, body_size=body_size,
                               reason=f"size {size} ranked #{level} above body {body_size}",
                               text=text[:120], block=blk["rk"])
            nodes.append({"type": "heading", "level": level, "text": text,
                          "id": hid, "page": blk["page"], "bbox": blk["bbox"],
                          "rk": rk, "data": prov})
        elif _is_bullet_list(blk):
            items = [re.sub(f"^[{re.escape(BULLETS)}]\\s*", "", l["text"]).strip()
                     for l in blk["lines"]]
            rk = ctx.log.entry("list", page=blk["page"], bbox=blk["bbox"],
                               items=len(items), reason="every line starts with a bullet char",
                               block=blk["rk"])
            nodes.append({"type": "list", "items": items, "page": blk["page"],
                          "bbox": blk["bbox"], "rk": rk, "data": prov})
        else:
            rk = ctx.log.entry("paragraph", page=blk["page"], bbox=blk["bbox"],
                               size=size, text=text[:120], block=blk["rk"])
            nodes.append({"type": "paragraph", "text": text, "page": blk["page"],
                          "bbox": blk["bbox"], "rk": rk, "data": prov})

    title = next((n["text"] for n in nodes if n["type"] == "heading" and n["level"] == 1),
                 ctx.source.stem)
    ctx.write_artifact("analyze", {"title": title, "body": nodes})


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
    ctx.log.entry("body-size", size=body,
                  distribution=dict(sizes.most_common(8)))
    return body


def _heading_levels(ctx, blocks, body_size):
    """Distinct sizes clearly above body size, ranked desc -> h1, h2, ..."""
    cand = sorted({_dominant_size(b) for b in blocks
                   if _dominant_size(b) > body_size * 1.15}, reverse=True)
    levels = {size: min(i + 1, 6) for i, size in enumerate(cand)}
    ctx.log.entry("heading-levels", body_size=body_size,
                  mapping={str(s): lv for s, lv in levels.items()})
    return levels


def _looks_like_heading(text):
    return 0 < len(text) <= 200 and not text.rstrip().endswith((".", ";", ":"))


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
