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

VERSION = 35

# chars: [uc, l, b, r, t, fontIdx, size, colorIdx]
UC, L, B, R, T, FONT, SIZE, COLOR = range(8)

# Width-bold fallback: some PDFs render bold as a HEAVIER WEIGHT OF THE SAME
# NAMED FONT — pdfium (and pdfminer/PyMuPDF) report identical name/weight/flags
# for bold and regular, so name-based emphasis is blind. The only signal left is
# glyph width: bold glyphs of the same letter are consistently wider. We detect
# fonts that are used in two weights (per-letter widths are bimodal) and split
# the wide glyphs into a synthetic bold font index, which the existing
# fontRuns + name/weight emphasis machinery then treats as <strong>.
_WIDTH_GAP = 0.045        # ≥4.5% gap between a letter's two width clusters
_VALLEY_RATIO = 4.0       # inter-cluster gap must dwarf the typical intra gap
_MIN_SAMPLES = 8          # per-letter samples needed to trust a cluster split
_MIN_BIMODAL_LETTERS = 5  # a font must be bimodal across this many letters


def _median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _cluster_centers(ws):
    """Split a letter's widths into two weight clusters — but ONLY if they are
    genuinely bimodal: the gap between them must be a real VALLEY, i.e. much
    larger than the typical gap within a cluster. A single-weight font with
    naturally spread widths (old-style serifs) has evenly-sized gaps and is
    rejected here; a true second weight leaves one gap that dwarfs the rest.
    Returns (regular, bold, ratio) or None."""
    s = sorted(ws)
    if len(s) < _MIN_SAMPLES:
        return None
    lo_i, hi_i = len(s) // 6, len(s) * 5 // 6          # ignore extreme outliers
    gaps = sorted((s[i + 1] - s[i]) for i in range(len(s) - 1))
    typical = gaps[len(gaps) // 2] or 1e-6             # median consecutive gap
    best, idx = 0.0, None
    for i in range(lo_i, hi_i):
        g = s[i + 1] - s[i]
        if s[i] > 0 and g / s[i] > best:
            best, idx = g / s[i], i
    if idx is None or best < _WIDTH_GAP:
        return None
    if (s[idx + 1] - s[idx]) < _VALLEY_RATIO * typical:  # not a real valley
        return None
    lo, hi = s[:idx + 1], s[idx + 1:]
    if len(lo) < 3 or len(hi) < 3:
        return None
    reg, bold = _median(lo), _median(hi)
    return reg, bold, bold / reg


_WORD_BOLD_RATIO = 1.045   # a word whose mean glyph-width ratio clears this is bold

# name weight tokens (longest/compound first so 'semibold' beats 'bold')
_NAME_WEIGHTS = [
    ("extrablack", 950), ("ultrablack", 950), ("extrabold", 800), ("ultrabold", 800),
    ("semibold", 600), ("demibold", 600), ("extralight", 200), ("ultralight", 200),
    ("black", 900), ("heavy", 900), ("bold", 700), ("medium", 500), ("demi", 600),
    ("semi", 600), ("light", 300), ("thin", 100), ("book", 400), ("regular", 400),
    ("normal", 400), ("roman", 400), ("hea", 900), ("blk", 900), ("bd", 700),
    ("sb", 600), ("dem", 600), ("med", 500), ("boo", 400), ("reg", 400), ("lt", 300),
]


def _name_weight(name):
    low = (name or "").lower()
    for tok, w in _NAME_WEIGHTS:
        if tok in low:
            return w
    return 400


def _family_key(name):
    """Family name with subset prefix, weight/style tokens, and non-letters
    stripped — so 'ABCDEF+ProximaNova-Bold' and 'ProximaNova-Light' group."""
    low = re.sub(r"^[a-z0-9]+\+", "", (name or "").lower())
    low = re.sub(r"[^a-z]", "", low)
    for tok, _ in _NAME_WEIGHTS:
        low = low.replace(tok, "")
    for tok in ("italic", "ital", "oblique", "obl", "condensed", "cond", "sc"):
        low = low.replace(tok, "")
    return low


def _split_width_bold_fonts(ctx, ex):
    """Detect fonts used in two weights under one name (per-letter widths are
    bimodal) and reassign the heavier glyphs to a synthetic bold font index.
    Decision is per WORD (mean of each glyph's width / its letter's regular
    baseline) — averaging cancels the per-glyph noise that fragments round
    letters — then punctuation gaps between bold words are filled so a phrase
    stays one contiguous run. Mutates ex (chars + fonts) in place."""
    fonts = ex["fonts"]
    # Only fonts whose FAMILY embeds a single weight are candidates: if a family
    # ships a real -Bold/-Semibold, the bold text lives in THAT named font and
    # name-based detection already catches it — width-splitting would double up.
    # gates' OverusedGrotesk ships only -Light yet renders bold → exactly this.
    fam_weights = defaultdict(set)
    for f in fonts:
        fam_weights[_family_key(f.get("name", ""))].add(_name_weight(f.get("name", "")))

    # width PER POINT (width / font size): the same font at 8pt vs 10pt has very
    # different absolute widths but identical width-per-point — normalizing by
    # size is what isolates a true weight difference from a mere size difference.
    def _wp(c):
        return (c[R] - c[L]) / c[SIZE] if c[SIZE] else 0

    widths = defaultdict(lambda: defaultdict(list))
    for page in ex["pages"]:
        for c in page["chars"]:
            if c[UC].isalpha() and c[SIZE]:
                widths[c[FONT]][c[UC]].append(_wp(c))
    total_glyphs = sum(len(ws) for f in widths.values() for ws in f.values())

    for fi in list(widths):
        fname = fonts[fi].get("name", "")
        fcount = sum(len(ws) for ws in widths[fi].values())
        # candidate only if (a) it's a primary BODY font (where a missing bold is
        # both common and glaring — display/accent fonts used for a few words are
        # excluded), and (b) its family ships ONE light/regular/medium weight, so
        # the bold can't already be a named sibling.
        if not total_glyphs or fcount / total_glyphs < 0.25:
            continue
        if len(fam_weights[_family_key(fname)]) != 1 or _name_weight(fname) > 500:
            continue
        centers = {ch: c for ch, ws in widths[fi].items()
                   if (c := _cluster_centers(ws)) is not None}
        if len(centers) < _MIN_BIMODAL_LETTERS:        # not a two-weight font
            continue
        baseline = {}                                  # per-letter regular width
        for ch, ws in widths[fi].items():
            if len(ws) >= 4:
                s = sorted(ws)
                baseline[ch] = s[int(len(s) * 0.3)]

        # mark bold glyphs page by page, by word, then gap-fill punctuation
        marks = {}        # id(page) -> set of char indices that are bold
        words = bold_words = 0
        bold_scores = []
        for page in ex["pages"]:
            chars = page["chars"]
            mask = [False] * len(chars)
            i, n = 0, len(chars)
            while i < n:
                if not (chars[i][FONT] == fi and chars[i][UC].isalpha()):
                    i += 1
                    continue
                j = i
                ratios = []
                while j < n and chars[j][FONT] == fi and chars[j][UC].isalpha():
                    b = baseline.get(chars[j][UC])
                    if b and chars[j][SIZE]:
                        ratios.append(_wp(chars[j]) / b)
                    j += 1
                words += 1
                score = sum(ratios) / len(ratios) if ratios else 0
                if ratios and score >= _WORD_BOLD_RATIO:
                    bold_words += 1
                    bold_scores.append(score)
                    for k in range(i, j):
                        mask[k] = True
                i = j
            # gap-fill: same-font punctuation/space between two bold glyphs (e.g.
            # the comma+space in "Second, losses") joins the run
            for a in range(len(chars)):
                if mask[a] or chars[a][FONT] != fi:
                    continue
                nxt = next((b for b in range(a + 1, min(a + 4, len(chars)))
                            if mask[b]), None)
                if nxt and any(mask[b] for b in range(max(0, a - 3), a)):
                    mask[a] = True
            marks[id(page)] = {k for k, m in enumerate(mask) if m}

        # Reject natural variance (single-weight serifs like ACaslonPro whose
        # widths spread enough to clip the threshold): a REAL second weight forms
        # a cluster clearly above the regular body, so its bold words score high
        # on average. A tail of barely-over words (median ~1.05) is just noise.
        if not words or not (0.01 <= bold_words / words <= 0.6):
            continue
        if not bold_scores or _median(bold_scores) < 1.075:
            ctx.log.entry("width-bold-skip", font=fname,
                          reason="bold cluster not separated from body",
                          bold_median=round(_median(bold_scores), 3) if bold_scores else 0)
            continue
        base = fonts[fi]
        syn = {"name": base.get("name", ""), "weight": max(base.get("weight", 400), 700),
               "flags": base.get("flags", 0), "synthetic_bold": True}
        fonts.append(syn)
        bidx = len(fonts) - 1
        moved = 0
        for page in ex["pages"]:
            sel = marks.get(id(page)) or set()
            for k in sel:
                page["chars"][k][FONT] = bidx
                moved += 1
        ctx.log.entry("width-bold-split", font=base.get("name", ""), font_idx=fi,
                      synthetic_idx=bidx, ratio=round(_median([r for _, _, r in centers.values()]), 3),
                      letters=len(centers), bold_words=bold_words, words=words,
                      glyphs_moved=moved)


def run(ctx):
    ex = ctx.artifact("extract")
    _split_width_bold_fonts(ctx, ex)
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
                # vertically detached) is a real break
                split = c[T] < prev[B] or c[B] > prev[T]
            if split:
                lines.append(_finish_line(cur, links, fills))
                cur = []
        cur.append(c)
    if cur:
        lines.append(_finish_line(cur, links, fills))
    return [ln for ln in lines if ln["text"].strip()]


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
    chars = sorted((c for i, c in enumerate(chars) if i not in drop),
                   key=lambda c: c[L])
    space_em = _space_threshold(chars)
    text = []
    src = []  # source char (or None for synthesized spaces), parallel to text
    prev_r = None
    sizes = Counter()
    fonts = Counter()
    colors = Counter()
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
    """True when line `r` is the top of a column: ≥2 other lines share its left
    edge and sit below it. Such a left margin is a recurring column edge, so a
    fragment bridging into `r` from the left is crossing the gutter, not
    continuing a visual line."""
    x0 = r["bbox"][0]
    r_mid = (r["bbox"][1] + r["bbox"][3]) / 2
    below = 0
    for k, ln in enumerate(lines):
        if k == i or k == j:
            continue
        if (ln["bbox"][1] + ln["bbox"][3]) / 2 >= r_mid:
            continue  # not below r (PDF y increases upward)
        if abs(ln["bbox"][0] - x0) <= 3.0:
            below += 1
            if below >= 2:
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
            if 0 <= gap <= limit and same_size and same_case:
                cur["lines"].append(ln)
                if gap > 0.9 * height:
                    cur["pitch"] = True
                continue
        cur = {"lines": [ln]}
        blocks.append(cur)
    for blk in blocks:
        bs = [l["bbox"] for l in blk["lines"]]
        blk["bbox"] = [min(b[0] for b in bs), min(b[1] for b in bs),
                       max(b[2] for b in bs), max(b[3] for b in bs)]
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
