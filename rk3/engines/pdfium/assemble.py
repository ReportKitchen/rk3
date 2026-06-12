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

VERSION = 18

# chars: [uc, l, b, r, t, fontIdx, size, colorIdx]
UC, L, B, R, T, FONT, SIZE, COLOR = range(8)


def run(ctx):
    ex = ctx.artifact("extract")
    all_blocks = []
    for page in ex["pages"]:
        lines = _merge_baseline_fragments(
            ctx, _lines(page["chars"], page.get("links", [])), page["n"])
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
        "pages": [{"n": p["n"], "width": p["width"], "height": p["height"],
                   "objects": p.get("objects", []),
                   "tagged": p.get("tagged", [])}
                  for p in ex["pages"]],
        "blocks": kept,
        "fonts": ex["fonts"],
        "colors": ex["colors"],
    })


def _lines(chars, links):
    """Group chars into lines following pdfium's content order, breaking on
    vertical jumps or large backward horizontal jumps."""
    lines = []
    cur = []
    for c in chars:
        if c[UC] in ("\r", "\n"):
            continue
        # spaces often have degenerate boxes; they never trigger a break, and
        # break checks compare against the last *visible* char
        if cur and c[UC] != " ":
            prev = next((x for x in reversed(cur) if x[UC] != " "), cur[-1])
            size = max(c[SIZE], 1.0)
            v_mid_prev = (prev[B] + prev[T]) / 2
            v_mid = (c[B] + c[T]) / 2
            if abs(v_mid - v_mid_prev) > 0.45 * size or c[L] < prev[L] - 2 * size:
                lines.append(_finish_line(cur, links))
                cur = []
        cur.append(c)
    if cur:
        lines.append(_finish_line(cur, links))
    return [ln for ln in lines if ln["text"].strip()]


def _finish_line(chars, links):
    chars = sorted(chars, key=lambda c: c[L])
    # some PDFs place space chars at geometrically impossible positions
    # ("i sjust"); a space whose neighbors nearly touch is a lie — drop it,
    # gap-synthesis below re-derives spacing from actual geometry
    cleaned = []
    for idx, c in enumerate(chars):
        if c[UC] == " " and c[R] - c[L] < 0.3:  # zero-width space glyph
            prev = cleaned[-1] if cleaned else None
            nxt = next((x for x in chars[idx + 1:] if x[UC] != " "), None)
            gap = (nxt[L] - prev[R]) if prev is not None and nxt is not None \
                else 0.0  # boundary zero-width spaces carry no evidence
            # judge against the NEIGHBORS' size: these glyphs lie about
            # their own (size 1, untransformed)
            ref = max((prev or c)[SIZE], (nxt or c)[SIZE], 1.0)
            if gap < 0.12 * ref:
                continue
        cleaned.append(c)
    chars = cleaned
    text = []
    src = []  # source char (or None for synthesized spaces), parallel to text
    prev_r = None
    sizes = Counter()
    fonts = Counter()
    colors = Counter()
    space_em = _space_threshold(chars)
    for c in chars:
        # synthesize a space on a visible horizontal gap (pdfium often includes
        # real space chars, but not always); threshold is adaptive per line —
        # letter-gap and word-gap sizes vary wildly between fonts/documents
        if prev_r is not None and c[L] - prev_r > space_em * max(c[SIZE], 1.0) \
                and text and text[-1] != " " and c[UC] != " ":
            text.append(" ")
            src.append(None)
        # unmapped control glyphs in symbol fonts are almost always hyphens
        ch = "-" if ord(c[UC]) < 32 else c[UC]
        if not (ch == " " and (not text or text[-1] == " ")):
            text.append(ch)
            src.append(c)
        prev_r = c[R]
        sizes[c[SIZE]] += 1
        fonts[c[FONT]] += 1
        colors[c[COLOR]] += 1
    # strip() equivalent that keeps src aligned; remember stripped boundary
    # spaces — but only ones that physically exist (real width or a
    # synthesized gap). Zero-width space glyphs parked at the previous word's
    # coordinates are typesetting lies and must not force a joiner space.
    orig_len = len(text)
    start = 0
    end = orig_len
    while start < end and text[start] == " ":
        start += 1
    while end > start and text[end - 1] == " ":
        end -= 1

    def _real_space(seg):
        return any(c is None or (c[R] - c[L]) > 0.3 for c in seg)

    space_before = _real_space(src[:start])
    space_after = _real_space(src[end:])
    text, src = text[start:end], src[start:end]

    dom_size = sizes.most_common(1)[0][0]
    line = {
        "text": "".join(text),
        "bbox": [min(c[L] for c in chars), min(c[B] for c in chars),
                 max(c[R] for c in chars), max(c[T] for c in chars)],
        "size": dom_size,
        "fontIdx": fonts.most_common(1)[0][0],
        "colorIdx": colors.most_common(1)[0][0],
    }
    if space_before:
        line["spaceBefore"] = True
    if space_after:
        line["spaceAfter"] = True
    sups = _sup_ranges(src, dom_size)
    if sups:
        line["sups"] = sups
    link_ranges = _link_ranges(src, links)
    if link_ranges:
        line["links"] = link_ranges
    color_runs = _color_runs(src, line["colorIdx"])
    if color_runs:
        line["colors"] = color_runs
    return line


def _color_runs(src, dom_color):
    """Ranges of chars colored differently from the line's dominant color
    (link styling, colored emphasis): [[s, e, colorIdx], ...]."""
    runs = []
    cur_color, start = None, None
    for i, c in enumerate(src):
        col = c[COLOR] if c is not None else cur_color  # spaces inherit
        if col != cur_color:
            if cur_color is not None and cur_color != dom_color:
                runs.append([start, i, cur_color])
            cur_color, start = col, i
    if cur_color is not None and cur_color != dom_color:
        runs.append([start, len(src), cur_color])
    return [r for r in runs if r[1] - r[0] >= 2]


def _space_threshold(chars):
    """Per-line word-gap threshold (em): find the split between the letter-gap
    cluster and the word-gap cluster in this line's gap distribution. Falls
    back to a conservative 0.25 em when the line has no clear two clusters."""
    gaps = []
    prev_r = None
    for c in chars:
        if c[UC] == " ":
            continue
        if prev_r is not None:
            g = (c[L] - prev_r) / max(c[SIZE], 1.0)
            if g > 0.01:
                gaps.append(g)
        prev_r = c[R]
    if len(gaps) < 4:
        return 0.25
    gaps.sort()
    best_jump, thresh = 0.0, 0.25
    for a, b in zip(gaps, gaps[1:]):
        if b >= 0.13 and b > a * 1.7 and (b - a) > best_jump:
            best_jump, thresh = b - a, (a + b) / 2
    return max(thresh, 0.10)


def _sup_ranges(src, dom_size):
    """Index ranges of superscript chars: clearly smaller than the line's
    dominant size and raised above its baseline."""
    bases = [c[B] for c in src if c and c[SIZE] >= 0.8 * dom_size]
    if not bases:
        return []
    base_b = sorted(bases)[len(bases) // 2]
    flags = [bool(c) and c[SIZE] <= 0.8 * dom_size
             and (c[B] - base_b) > 0.15 * dom_size for c in src]
    return _runs(flags)


def _link_ranges(src, links):
    """Index ranges covered by link annotation rects, with their targets."""
    out = []
    for l, b, r, t, target in links:
        flags = []
        for c in src:
            if not c:  # synthesized space: inherit, so it can't split a link
                flags.append(bool(flags) and flags[-1])
                continue
            cx, cy = (c[L] + c[R]) / 2, (c[B] + c[T]) / 2
            flags.append(l <= cx <= r and b <= cy <= t)
        while flags and flags[-1] and src[len(flags) - 1] is None:
            flags[-1] = False  # but never end on an inherited space
        out.extend([s, e, target] for s, e in _runs(flags))
    return out


def _runs(flags):
    runs = []
    start = None
    for i, f in enumerate(flags):
        if f and start is None:
            start = i
        elif not f and start is not None:
            runs.append([start, i])
            start = None
    if start is not None:
        runs.append([start, len(flags)])
    return runs


def _merge_baseline_fragments(ctx, lines, page_n):
    """pdfium sometimes emits one visual line as multiple content runs (out of
    content order). Merge fragments sharing a baseline that sit horizontally
    adjacent; the merged line keeps the earlier fragment's position in reading
    order so multi-column content order is not disturbed."""

    def mid(ln):
        return (ln["bbox"][1] + ln["bbox"][3]) / 2

    used = [False] * len(lines)
    out = []
    for i, ln in enumerate(lines):
        if used[i]:
            continue
        cur = ln
        changed = True
        while changed:
            changed = False
            for j in range(i + 1, len(lines)):
                if used[j]:
                    continue
                other = lines[j]
                size = max(cur["size"], other["size"], 1.0)
                sup = _sup_of(cur, other)
                # superscripts sit raised, so allow a looser vertical match
                tol = 0.75 if sup is not None else 0.35
                if abs(mid(cur) - mid(other)) > tol * size:
                    continue
                left, right = (cur, other) if cur["bbox"][0] <= other["bbox"][0] else (other, cur)
                gap = right["bbox"][0] - left["bbox"][2]
                # fragments may overlap by most of a glyph (kerned runs split
                # across text objects), but near-total overlap means a drawn-
                # twice effect, not a continuation
                if not (-0.8 * size <= gap <= 1.5 * size):
                    continue
                ctx.log.entry("merge-baseline", page=page_n, gap=round(gap, 2),
                              sup=(sup["text"][:12] if sup is not None else None),
                              left=left["text"][-40:], right=right["text"][:40])
                # space on a visible gap, or on a word-boundary signature
                # (new fragment starts a capitalized word) even when the gap
                # is tiny or negative because a space glyph was never emitted.
                # No space when attaching a superscript itself, but when the
                # *left* side ends in a superscript and prose follows, the
                # space after the marker was lost with the run split
                left_ends_sup = any(e == len(left["text"])
                                    for s, e in left.get("sups", []))
                if sup is not None:
                    joiner = ""
                elif left_ends_sup and right["text"][:1].isalpha():
                    joiner = " "
                elif left.get("spaceAfter") or right.get("spaceBefore"):
                    joiner = " "  # the PDF had a real space at this boundary
                else:
                    joiner = " " if (gap > 0.2 * size or
                                     right["text"][:1].isupper()) else ""
                keep = left if len(left["text"]) >= len(right["text"]) else right
                shift = len(left["text"]) + len(joiner)
                cur = {
                    "text": left["text"] + joiner + right["text"],
                    "bbox": [min(left["bbox"][0], right["bbox"][0]),
                             min(left["bbox"][1], right["bbox"][1]),
                             max(left["bbox"][2], right["bbox"][2]),
                             max(left["bbox"][3], right["bbox"][3])],
                    "size": keep["size"], "fontIdx": keep["fontIdx"],
                    "colorIdx": keep["colorIdx"],
                }
                if left.get("spaceBefore"):
                    cur["spaceBefore"] = True
                if right.get("spaceAfter"):
                    cur["spaceAfter"] = True
                for key in ("sups", "links", "colors"):
                    merged = list(left.get(key, []))
                    for rng in right.get(key, []):
                        merged.append([rng[0] + shift, rng[1] + shift, *rng[2:]])
                    if merged:
                        cur[key] = merged
                if sup is not None:  # record the absorbed superscript's range
                    rng = ([shift, shift + len(right["text"])] if sup is right
                           else [0, len(left["text"])])
                    cur.setdefault("sups", []).append(rng)
                used[j] = True
                changed = True
        out.append(cur)
    return out


def _is_caps(text):
    letters = [c for c in text if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters)


def _sup_of(a, b):
    """If one line is a superscript fragment of the other (much smaller and
    raised off the partner's baseline), return that line, else None."""
    small, big = (a, b) if a["size"] <= b["size"] else (b, a)
    if small["size"] > 0.82 * big["size"]:
        return None
    if len(small["text"]) > 4:
        return None
    if small["bbox"][1] > big["bbox"][1] + 0.1 * big["size"]:
        return small
    return None


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
            # an ALL-CAPS kicker followed by mixed-case prose (or vice versa)
            # is a boundary even at body size
            same_case = _is_caps(ln["text"]) == _is_caps(last["text"])
            if 0 <= gap <= 0.9 * height and same_size and same_case:
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

    # capped: in long docs many pages legitimately lack the footer (covers,
    # worksheets), but 8 identical edge-zone repeats is conclusive regardless
    min_repeats = max(3, min(8, round(0.4 * n_pages)))
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
