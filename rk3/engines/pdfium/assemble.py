"""Assemble stage: chars -> lines -> blocks; strip running headers/footers
and standalone page numbers (recorded in the debug log, with the original
page kept as provenance on every block).

Artifact: blocks.json
  { "pages": [ { "n", "width", "height" } ],
    "blocks": [ { "page", "bbox": [l, b, r, t], "rk",
                  "lines": [ { "text", "bbox", "size", "fontIdx", "colorIdx" } ] } ],
    "fonts": [...], "colors": [...] }   # passed through from extract
"""

import re
from collections import Counter

VERSION = 1

# chars: [uc, l, b, r, t, fontIdx, size, colorIdx]
UC, L, B, R, T, FONT, SIZE, COLOR = range(8)


def run(ctx):
    ex = ctx.artifact("extract")
    all_blocks = []
    for page in ex["pages"]:
        lines = _lines(page["chars"])
        blocks = _blocks(lines)
        for blk in blocks:
            blk["page"] = page["n"]
        all_blocks.extend(blocks)

    page_dims = {p["n"]: (p["width"], p["height"]) for p in ex["pages"]}
    kept = _strip_repeating(ctx, all_blocks, page_dims, len(ex["pages"]))

    for blk in kept:
        blk["rk"] = ctx.log.entry(
            "block", page=blk["page"], bbox=blk["bbox"],
            lines=len(blk["lines"]), text=blk["lines"][0]["text"][:80])

    ctx.write_artifact("assemble", {
        "pages": [{"n": p["n"], "width": p["width"], "height": p["height"]}
                  for p in ex["pages"]],
        "blocks": kept,
        "fonts": ex["fonts"],
        "colors": ex["colors"],
    })


def _lines(chars):
    """Group chars into lines following pdfium's content order, breaking on
    vertical jumps or large backward horizontal jumps."""
    lines = []
    cur = []
    for c in chars:
        if c[UC] in ("\r", "\n"):
            continue
        if cur:
            prev = cur[-1]
            size = max(c[SIZE], 1.0)
            v_mid_prev = (prev[B] + prev[T]) / 2
            v_mid = (c[B] + c[T]) / 2
            if abs(v_mid - v_mid_prev) > 0.45 * size or c[L] < prev[L] - 2 * size:
                lines.append(_finish_line(cur))
                cur = []
        cur.append(c)
    if cur:
        lines.append(_finish_line(cur))
    return [ln for ln in lines if ln["text"].strip()]


def _finish_line(chars):
    chars = sorted(chars, key=lambda c: c[L])
    text = []
    prev_r = None
    sizes = Counter()
    fonts = Counter()
    colors = Counter()
    for c in chars:
        # synthesize a space on a visible horizontal gap (pdfium often includes
        # real space chars, but not always)
        if prev_r is not None and c[L] - prev_r > 0.25 * max(c[SIZE], 1.0) \
                and text and text[-1] != " " and c[UC] != " ":
            text.append(" ")
        if not (c[UC] == " " and (not text or text[-1] == " ")):
            text.append(c[UC])
        prev_r = c[R]
        sizes[c[SIZE]] += 1
        fonts[c[FONT]] += 1
        colors[c[COLOR]] += 1
    return {
        "text": "".join(text).strip(),
        "bbox": [min(c[L] for c in chars), min(c[B] for c in chars),
                 max(c[R] for c in chars), max(c[T] for c in chars)],
        "size": sizes.most_common(1)[0][0],
        "fontIdx": fonts.most_common(1)[0][0],
        "colorIdx": colors.most_common(1)[0][0],
    }


def _blocks(lines):
    """Merge consecutive lines into blocks on small vertical gaps and similar
    dominant font size. PDF y decreases down the page."""
    blocks = []
    cur = None
    for ln in lines:
        if cur is not None:
            last = cur["lines"][-1]
            gap = last["bbox"][1] - ln["bbox"][3]  # prev bottom - this top
            height = max(ln["size"], 1.0)
            same_size = abs(ln["size"] - last["size"]) < 0.6
            if 0 <= gap <= 0.9 * height and same_size:
                cur["lines"].append(ln)
                continue
        cur = {"lines": [ln]}
        blocks.append(cur)
    for blk in blocks:
        bs = [l["bbox"] for l in blk["lines"]]
        blk["bbox"] = [min(b[0] for b in bs), min(b[1] for b in bs),
                       max(b[2] for b in bs), max(b[3] for b in bs)]
    return blocks


def _strip_repeating(ctx, blocks, page_dims, n_pages):
    """Drop running headers/footers (same normalized text near the same edge
    position on several pages) and standalone page-number lines."""
    zones = (0.10, 0.10)  # top / bottom fraction of page height

    def zone(blk):
        w, h = page_dims[blk["page"]]
        if blk["bbox"][3] > h * (1 - zones[0]):
            return "top"
        if blk["bbox"][1] < h * zones[1]:
            return "bottom"
        return None

    def norm(blk):
        text = " ".join(l["text"] for l in blk["lines"])
        return re.sub(r"\d+", "#", text).strip().lower()

    seen = Counter()
    for blk in blocks:
        z = zone(blk)
        if z:
            seen[(z, norm(blk))] += 1

    min_repeats = max(3, round(0.4 * n_pages))
    kept = []
    for blk in blocks:
        z = zone(blk)
        text = " ".join(l["text"] for l in blk["lines"]).strip()
        if z and seen[(z, norm(blk))] >= min_repeats:
            ctx.log.entry("strip-running", page=blk["page"], zone=z, text=text[:80],
                          repeats=seen[(z, norm(blk))], min_repeats=min_repeats)
            continue
        if z and re.fullmatch(r"(page\s*)?\d{1,4}", text, re.I):
            ctx.log.entry("strip-pagenum", page=blk["page"], zone=z, text=text)
            continue
        kept.append(blk)
    return kept
