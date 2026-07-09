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
from collections import Counter, defaultdict

VERSION = 53

# lowercase letters with neither ascender nor descender — their glyph tops sit
# at x-height in normal text but reach the CAP line when a display font renders
# an all-caps run from lowercase codepoints (webified §5.1 caps mirroring)
_SHORT_X = set("acemnorsuvwxz")


def _line_caps(chars):
    """True when a run is displayed ALL-CAPS from (usually) lowercase
    codepoints: its short x-height letters all reach cap height — a signal a
    normal mixed-case run never shows (an ordinary 'e'/'a'/'o' stops at
    x-height). Lets render mirror the source's ALL-CAPS kickers/labels/headings
    (race p9 'FIGURE 2 | RACE/ETHNICITY', 'KEY FINDING 1', 'IN THEIR OWN
    WORDS'). Genuinely-uppercase codepoints have no short letters and return
    False — they already render caps, no mirroring needed."""
    alpha = [c for c in chars if c[UC].isalpha()]
    if len(alpha) < 3:
        return False
    # a DROP CAP sinks `base` (min bottom) a line or two below the row without
    # raising the cap ceiling, so every ordinary first-line letter then measures
    # as cap-height and the whole paragraph gets falsely shouted (edf p6 'E'DF
    # subsidiary… → ALL CAPS body). Judge caps from the line's OWN body glyphs:
    # drop any glyph much taller than the median (drop caps, oversized initials).
    heights = sorted(c[T] - c[B] for c in alpha)
    med_h = heights[len(heights) // 2]
    body = [c for c in alpha if (c[T] - c[B]) <= 1.6 * med_h]
    if len(body) < 3:
        return False
    short = [c for c in body if c[UC] in _SHORT_X]
    if not short:
        return False
    base = min(c[B] for c in body)
    cap_h = max(c[T] for c in body) - base
    if cap_h <= 0.5:
        return False
    return all((c[T] - base) >= 0.85 * cap_h for c in short)

# chars: [uc, l, b, r, t, fontIdx, size, colorIdx]
UC, L, B, R, T, FONT, SIZE, COLOR = range(8)

def run(ctx):
    ex = ctx.artifact("extract")
    all_blocks = []
    for page in ex["pages"]:
        # candidate text-highlight rects: small filled paths (height-checked
        # per line later; big callout/cell fills never qualify)
        fills = [(o[1], o[2], o[3], o[4], o[5])
                 for o in page.get("objects", [])
                 if o[0] == 2 and o[7] and o[5] is not None
                 and (o[4] - o[2]) < 40]
        lines = _merge_baseline_fragments(
            ctx, _lines(page["chars"], page.get("links", []), fills),
            page["n"])
        blocks = _blocks(lines)
        for blk in blocks:
            blk["page"] = page["n"]
        all_blocks.extend(blocks)

    all_blocks = _join_amp_wraps(ctx, all_blocks)
    page_dims = {p["n"]: (p["width"], p["height"]) for p in ex["pages"]}
    kept, running_sigs = _strip_repeating(ctx, all_blocks, page_dims, len(ex["pages"]))

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
        "runningHeaders": sorted(running_sigs),
        "fonts": ex["fonts"],
        "colors": ex["colors"],
        "embeddedFonts": ex.get("embeddedFonts", {}),
        "fontsComplete": ex.get("fontsComplete", True),
    })


def _lines(chars, links, fills=()):
    """Group chars into lines following pdfium's content order, breaking on
    vertical jumps or large backward horizontal jumps."""
    lines = []
    cur = []
    for c in chars:
        if c[UC] in ("\r", "\n"):
            continue
        # spaces and partial-height glyphs (quotes, periods, commas — boxes
        # anchored to one end of the line) never trigger a break and never
        # serve as the comparison reference; thresholds scale with the larger
        # glyph so superscripts don't split off
        if cur and c[UC] != " ":
            prev = next((x for x in reversed(cur)
                         if x[UC] != " " and _full_height(x)), cur[-1])
            if _full_height(c):
                size = max(c[SIZE], prev[SIZE], 1.0)
                v_mid_prev = (prev[B] + prev[T]) / 2
                v_mid = (c[B] + c[T]) / 2
                split = (abs(v_mid - v_mid_prev) > 0.45 * size
                         or c[L] < prev[L] - 2 * size)
            else:
                # partial-height glyphs anchor to one end of the line, so
                # their midpoints wander - but they still overlap its band;
                # one that doesn't (a symbol-font bullet of the next line,
                # vertically detached) is a real break. Compare against the
                # whole line's band, not the previous char: a closing quote /
                # apostrophe sits at ascender height, so its bottom can clear a
                # short lowercase top (627.8 > 627.1 'n') yet still overlap the
                # line's ascenders. Using prev alone split the quote off.
                fulls = [x for x in cur if x[UC] != " " and _full_height(x)]
                band_top = max((x[T] for x in fulls), default=prev[T])
                band_bot = min((x[B] for x in fulls), default=prev[B])
                split = c[T] < band_bot or c[B] > band_top
            if split:
                lines.append(_finish_line(cur, links, fills))
                cur = []
        cur.append(c)
    if cur:
        lines.append(_finish_line(cur, links, fills))
    return [ln for ln in lines if ln["text"].strip()]


# the words that decide whether a drop cap 'A'/'I' joins its following token:
# cap + token completing one of these means the space is a sidebearing artifact
# ("A n oil" -> "An oil", "I n the" -> "In the"); anything else keeps the space
# ("A square mile"). English's only single-letter words are A and I, so all
# other caps always join ("E DF" -> "EDF").
_CAP_WORDS = frozenset(("An", "As", "At", "Am", "In", "It", "Is", "If"))


def _dropcap_join(prev_c, c):
    """A drop cap — an ornamental first glyph several times the body size — leaves
    a wide sidebearing that mimics a word gap ("E" before "DF subsidiary" sits
    5pt off, 0.5 body-em). Geometry can't tell "Aboard" (join) from "A square"
    (space): both hug the cap identically, so suppress the synthesized space for
    every cap except 'A'/'I' — those are decided by the _CAP_WORDS token test in
    the line-level repair (which also handles EXPLICIT space glyphs)."""
    return (prev_c is not None and prev_c[UC].isalpha()
            and prev_c[SIZE] >= 1.8 * max(c[SIZE], 1.0)
            and prev_c[UC] not in ("A", "a", "I", "i"))


def _finish_line(chars, links, fills=()):
    # Some PDFs place space chars at geometrically impossible positions: a space
    # whose x falls at or before the RIGHT edge of the char that PRECEDES it in
    # the content stream can't be a real gap there. ("Healt","h"," ",".") renders
    # "Health." but the trailing space, once x-sorted, would land between t and h
    # and split the word. Detect this in CONTENT order (before sorting) and drop
    # it; trust every other explicit space, so genuinely tight word gaps in dense
    # fonts ("of Agriculture") survive. Gap-synthesis below fills real gaps that
    # carry no space char at all.
    drop = set()
    prev_real = None
    for i, c in enumerate(chars):
        if c[UC] == " " and c[R] - c[L] < 0.3:  # zero-width space glyph
            if prev_real is not None and c[L] < prev_real[R] - 0.1:
                drop.add(i)
        elif c[UC] != " ":
            prev_real = c
    # x-sort to recover pdfium's occasional out-of-order glyphs — but an explicit
    # space whose recorded x lands AT/AFTER the next glyph (a positioning quirk:
    # the space's L is its post-advance position) would sort INTO the next word,
    # and the word-gap it left behind then gets re-synthesized: "review by" ->
    # "review b y". Pin each space's sort key to just before the next content
    # glyph so it stays where the content stream put it. Only quirky spaces move.
    kept = [c for i, c in enumerate(chars) if i not in drop]
    keys, next_l = [0.0] * len(kept), None
    for j in range(len(kept) - 1, -1, -1):
        c = kept[j]
        if c[UC] == " " and next_l is not None:
            keys[j] = min(c[L], next_l - 0.01)
        else:
            keys[j] = c[L]
            if c[UC] != " ":
                next_l = c[L]
    chars = [kept[j] for j in sorted(range(len(kept)), key=lambda j: (keys[j], j))]
    space_em = _space_threshold(chars)
    text = []
    src = []  # source char (or None for synthesized spaces), parallel to text
    prev_r = None
    prev_c = None  # previous source char (for drop-cap detection)
    sizes = Counter()
    fonts = Counter()
    colors = Counter()
    for c in chars:
        # synthesize a space on a visible horizontal gap (pdfium often includes
        # real space chars, but not always); threshold is adaptive per line —
        # letter-gap and word-gap sizes vary wildly between fonts/documents
        if prev_r is not None and c[L] - prev_r > space_em * max(c[SIZE], 1.0) \
                and text and text[-1] != " " and c[UC] != " " \
                and not (text[-1].isdigit() and c[UC].isdigit()) \
                and not _dropcap_join(prev_c, c):
            # ...except between two digits: tabular figures vary their gaps
            # ("2012" -> "201 2") but a number never contains a real space.
            text.append(" ")
            src.append(None)
        # unmapped control glyphs in symbol fonts are almost always hyphens
        ch = "-" if ord(c[UC]) < 32 else c[UC]
        if not (ch == " " and (not text or text[-1] == " ")):
            text.append(ch)
            src.append(c)
        prev_c = c
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
    # drop-cap space repair: an ornamental cap's sidebearing gap often arrives
    # as an EXPLICIT space glyph ("A"," ","n oil"), which the synthesis guard
    # (_dropcap_join) never sees. Decide once on the assembled line: the cap
    # joins its word — and 'A'/'I' DO join when the next token completes a
    # common short word ("A n oil" -> "An oil", "I n the" -> "In the") but
    # keep their space when it doesn't ("A square mile").
    if (len(text) > 2 and text[1] == " " and src[0] is not None
            and src[0][UC].isalpha()
            and src[0][SIZE] >= 1.8 * max(dom_size, 1.0)):
        tok = "".join(text[2:8]).split(" ", 1)[0]
        if text[0] not in "AaIi" or (text[0].upper() + tok.lower()) in _CAP_WORDS:
            del text[1]
            del src[1]
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
    if _line_caps(chars):
        line["caps"] = True
    sups = _sup_ranges(src, dom_size)
    if sups:
        line["sups"] = sups
    link_ranges = _link_ranges(src, links)
    if link_ranges:
        line["links"] = link_ranges
    color_runs = _color_runs(src, line["colorIdx"])
    if color_runs:
        line["colors"] = color_runs
    # ornamental drop cap: the line's first glyph is a letter several times the
    # body size. Record its scale + color + FONT so render can re-create the
    # visual cap via CSS (rubric §3: preserve by default) at its true weight —
    # a cap inside a <strong> lead would otherwise inherit bold it never had.
    if (src and src[0] is not None and src[0][UC].isalpha()
            and src[0][SIZE] >= 1.8 * max(dom_size, 1.0)):
        line["dropCap"] = [round(src[0][SIZE] / max(dom_size, 1.0), 2),
                           src[0][COLOR], src[0][FONT]]
    font_runs = _font_runs(src, line["fontIdx"])
    if font_runs:
        line["fontRuns"] = font_runs
    marks = _mark_runs(src, line, fills)
    if marks:
        line["marks"] = marks
    return line


def _mark_runs(src, line, fills):
    """Text highlights: a fill rect hugging part of the line (height within
    1.8x the text size, vertically overlapping it) marks the chars it covers,
    like the PDF highlighter tool: [[s, e, colorIdx], ...]. Tall fills are
    callout boxes and table cells, not highlights - excluded upstream and by
    the height check."""
    if not fills:
        return None
    lb, lt = line["bbox"][1], line["bbox"][3]
    runs = []
    for fl, fb, fr, ft, ci in fills:
        if ft - fb > 1.8 * max(line["size"], 1.0):
            continue
        if min(ft, lt) - max(fb, lb) < 0.5 * (lt - lb):
            continue
        s = e = None
        for idx, c in enumerate(src):
            if c is None:
                continue
            cx = (c[L] + c[R]) / 2
            if fl - 1 <= cx <= fr + 1:
                if s is None:
                    s = idx
                e = idx + 1
        if s is not None and e - s >= 2:
            runs.append([s, e, ci])
    runs.sort()
    merged = []
    for s, e, ci in runs:
        if merged and ci == merged[-1][2] and s <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e, ci])
    return merged or None


def _font_runs(src, dom_font):
    """Ranges of chars in a different font from the line's dominant one
    (inline bold/italic emphasis; also the style-signature miner's input)."""
    runs = []
    cur_font, start = None, None
    for i, c in enumerate(src):
        f = c[FONT] if c is not None else cur_font  # spaces inherit
        if f != cur_font:
            if cur_font is not None and cur_font != dom_font:
                runs.append([start, i, cur_font])
            cur_font, start = f, i
    if cur_font is not None and cur_font != dom_font:
        runs.append([start, len(src), cur_font])
    return [r for r in runs if r[1] - r[0] >= 3]


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


def _full_height(c):
    return (c[T] - c[B]) >= 0.35 * max(c[SIZE], 1.0)


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
                # don't bridge a column gutter: a same-baseline fragment set off
                # to the right that begins its own column (several lines share its
                # left edge below it) is the top of the next column, not a
                # continuation of this line. Skip short left fragments — drop caps
                # ("I"+"n the United States"), section numbers ("3.1"+title) and
                # marker letters ("B"+heading) legitimately attach across a gap.
                if (gap > 0.6 * size and len(left["text"].strip()) > 3
                        and _starts_column(right, lines, i, j)):
                    ctx.log.entry("merge-skip-gutter", page=page_n,
                                  gap=round(gap, 2), left=left["text"][-40:],
                                  right=right["text"][:40])
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
                for key in ("sups", "links", "colors", "fontRuns", "marks"):
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


def _starts_column(r, lines, i, j):
    """True when line `r` sits on a recurring column edge: ≥2 other lines share
    its left edge (above OR below). Such a left margin is a column boundary, so a
    same-baseline fragment bridging into `r` from the left is crossing the gutter,
    not continuing a visual line. Counting both directions is essential — the
    bottom line of a column has nothing below it, yet still sits on the gutter
    (this was fusing a left column's last line into the right column's last)."""
    x0 = r["bbox"][0]
    shared = 0
    for k, ln in enumerate(lines):
        if k == i or k == j:
            continue
        if abs(ln["bbox"][0] - x0) <= 3.0:
            shared += 1
            if shared >= 2:
                return True
    return False


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


def _line_pitch(lines):
    """Modal vertical gap between consecutive same-size lines - the page's
    line pitch. Typed documents (Word exports at 1.5/double spacing) set it
    well above the geometric merge threshold, with paragraph gaps in a
    separate cluster above it. Only trusted when well populated."""
    gaps = []
    for a, b in zip(lines, lines[1:]):
        if abs(a["size"] - b["size"]) >= 0.6:
            continue
        g = a["bbox"][1] - b["bbox"][3]
        if 0 <= g <= 2.2 * max(b["size"], 1.0):
            gaps.append(round(g))
    if len(gaps) < 8:
        return None
    mode, count = Counter(gaps).most_common(1)[0]
    return float(mode) if count >= 0.35 * len(gaps) else None


def _blocks(lines):
    """Merge consecutive lines into blocks on small vertical gaps and similar
    dominant font size. PDF y decreases down the page. The gap threshold
    adapts to the page's line pitch, so typed line breaks join into real
    paragraphs; pitch-joined blocks are marked (a document-level question
    lets the user keep the original breaks instead)."""
    pitch = _line_pitch(lines)
    blocks = []
    cur = None
    for ln in lines:
        if cur is not None:
            last = cur["lines"][-1]
            gap = last["bbox"][1] - ln["bbox"][3]  # prev bottom - this top
            height = max(ln["size"], 1.0)
            limit = 0.9 * height
            if pitch is not None and pitch > limit:
                limit = min(pitch + 0.45 * height, 1.7 * height)
            same_size = abs(ln["size"] - last["size"]) < 0.6
            # an ALL-CAPS kicker followed by mixed-case prose (or vice versa)
            # is a boundary even at body size
            same_case = _is_caps(ln["text"]) == _is_caps(last["text"])
            # Column guard: never weld a line into a paragraph it shares no
            # horizontal extent with. Interleaved two-column content arrives in
            # content order as a zig-zag of small vertical gaps; without this it
            # fuses left- and right-column lines into one block and splices
            # sentences mid-clause across the gutter. Same-column lines overlap
            # strongly; a gutter makes the overlap negative.
            overlap = min(cur["x1"], ln["bbox"][2]) - max(cur["x0"], ln["bbox"][0])
            same_col = overlap > 0.2 * min(cur["x1"] - cur["x0"],
                                           ln["bbox"][2] - ln["bbox"][0], 1.0) \
                if (cur["x1"] - cur["x0"]) > 0 else True
            if 0 <= gap <= limit and same_size and same_case and same_col:
                cur["lines"].append(ln)
                cur["x0"] = min(cur["x0"], ln["bbox"][0])
                cur["x1"] = max(cur["x1"], ln["bbox"][2])
                if gap > 0.9 * height:
                    cur["pitch"] = True
                continue
        cur = {"lines": [ln], "x0": ln["bbox"][0], "x1": ln["bbox"][2]}
        blocks.append(cur)
    for blk in blocks:
        bs = [l["bbox"] for l in blk["lines"]]
        blk["bbox"] = [min(b[0] for b in bs), min(b[1] for b in bs),
                       max(b[2] for b in bs), max(b[3] for b in bs)]
        blk.pop("x0", None); blk.pop("x1", None)
    return blocks


def _join_amp_wraps(ctx, blocks):
    """A block ending with '&' is a wrapped continuation — the next block on
    the page (same size, small gap) is its tail ('… Prevention &' / 'CHASE')."""
    out = []
    for blk in blocks:
        if out:
            prev = out[-1]
            last = prev["lines"][-1]
            gap = last["bbox"][1] - blk["lines"][0]["bbox"][3]
            if prev["page"] == blk["page"] \
                    and last["text"].rstrip().endswith("&") \
                    and abs(last["size"] - blk["lines"][0]["size"]) < 0.6 \
                    and 0 <= gap <= 1.8 * max(last["size"], 1.0):
                ctx.log.entry("join-amp", page=blk["page"],
                              left=last["text"][-30:],
                              right=blk["lines"][0]["text"][:30])
                prev["lines"].extend(blk["lines"])
                bs = [l["bbox"] for l in prev["lines"]]
                prev["bbox"] = [min(b[0] for b in bs), min(b[1] for b in bs),
                                max(b[2] for b in bs), max(b[3] for b in bs)]
                continue
        out.append(blk)
    return out


def _strip_repeating(ctx, blocks, page_dims, n_pages):
    """Drop running headers/footers and standalone page-number lines.

    A running header recurs at a page margin across many pages, but its text is
    NOT always identical. A book/report title is routinely paired with a
    per-section title ("INEQUALITY INC. | A Gilded Age of Division") and an
    embedded page number, so the full string changes every section and every
    page, and the number is inconsistently attached to the same block. Keying on
    the exact normalized string misses all of these — each variant falls below
    the repeat threshold even though the header is on most pages.

    So strip on three signals, any of which marks an edge-zone block as running:
      - its exact normalized text repeats on enough pages (the classic case);
      - its leading two tokens recur on enough pages (stable title, drifting
        tail — the section name and page number change, the title does not);
      - its trailing two tokens recur on enough pages (title trails the section
        name, the mirror layout).
    Counting DISTINCT PAGES (not blocks) lets a 7-page section plus its
    page-numbered variants sum past the threshold. The top/bottom-margin zone
    restriction keeps the token signals from touching body text — recurring
    leading words in a 10%-margin band across many pages are a header, not prose
    (whose first words differ every page)."""
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

    # capped: in long docs many pages legitimately lack the footer (covers,
    # worksheets), but 8 identical edge-zone repeats is conclusive regardless
    min_repeats = max(3, min(8, round(0.4 * n_pages)))

    # The fuzzy lead/trail signals (varying header text) need a higher bar than
    # exact repeats, because real recurring CONTENT can also share a prefix at a
    # stable position: a figure series ("Figure 12: …", "Figure 13: …") or a
    # per-chapter title ("CHAPTER 3. …"). The separator is page COVERAGE — a
    # running header sits in the margin of a large share of the document, while a
    # figure series or chapter title covers only a sliver. Require a third of the
    # pages (still floored at min_repeats for short docs).
    fuzzy_min = max(min_repeats, round(0.33 * n_pages))

    # signature = normalized text with ALL whitespace removed, so a dropped
    # space ("INC.EXECUTIVE" vs "INC. EXECUTIVE", a space-synthesis miss) can't
    # change it. The leading / trailing 12 chars are the stable ends of the
    # header that survive a drifting section name and page number.
    def sig(blk):
        return re.sub(r"\s+", "", norm(blk))

    # The fuzzy lead/trail signals are gated on POSITION: a running header recurs
    # at a consistent y-band, page after page. Recurring *content* with a shared
    # text shape — figure titles ("Figure 12: …", "Figure 13: …") or numbered
    # footnotes — sits wherever the figure or note falls, so its y scatters and
    # never accumulates in one band. Keying the signature with a top-edge band
    # (2% of page height) keeps those out while still folding every section /
    # page-number variant of the real header into one slot.
    def band(blk):
        h = page_dims[blk["page"]][1]
        return round(blk["bbox"][3] / h / 0.02)

    exact = Counter()
    head_pages = defaultdict(set)   # (zone, band, first 12 sig chars) -> pages
    tail_pages = defaultdict(set)   # (zone, band, last  12 sig chars) -> pages
    for blk in blocks:
        z = zone(blk)
        if not z:
            continue
        exact[(z, norm(blk))] += 1
        s = sig(blk)
        if len(s) >= 8:
            b = band(blk)
            head_pages[(z, b, s[:12])].add(blk["page"])
            tail_pages[(z, b, s[-12:])].add(blk["page"])

    def running(z, blk):
        if exact[(z, norm(blk))] >= min_repeats:
            return "exact"
        s = sig(blk)
        if len(s) >= 8:
            b = band(blk)
            if len(head_pages[(z, b, s[:12])]) >= fuzzy_min:
                return "lead"
            if len(tail_pages[(z, b, s[-12:])]) >= fuzzy_min:
                return "trail"
        return None

    kept, running_sigs = [], set()
    for blk in blocks:
        z = zone(blk)
        text = " ".join(l["text"] for l in blk["lines"]).strip()
        if z:
            by = running(z, blk)
            if by:
                ctx.log.entry("strip-running", page=blk["page"], zone=z,
                              text=text[:80], by=by, min_repeats=min_repeats)
                # remember the digit-masked signature: the SAME branding can also
                # appear off-margin (a cover eyebrow "EDF IMPACT 2023") where it
                # escapes stripping and mis-classifies as a heading — analyze uses
                # this set to demote it (running-header/footer, not a section head)
                sg = norm(blk)
                if len(sg) >= 10:
                    running_sigs.add(sg)
                continue
            if re.fullmatch(r"(page\s*)?\d{1,4}", text, re.I):
                ctx.log.entry("strip-pagenum", page=blk["page"], zone=z, text=text)
                continue
        kept.append(blk)
    return kept, running_sigs
