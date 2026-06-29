"""Wrap a PDF-embedded font program into a browser-servable OpenType file.

PDF embeds fonts as bare programs (FontFile/FontFile2/FontFile3): a TrueType
sfnt, or — most often for InDesign exports — a bare CFF (Type1C) with no sfnt
wrapper and no usable Unicode cmap. Browsers need an sfnt with a Unicode cmap.

`wrap_programs(datas, name)` takes ALL embedded programs that resolved to one
font name (a font is usually split into several per-page subsets, each covering
different glyphs) and unions them into a single served face — otherwise text
drawn from a subset other than the one we picked would render as tofu. Returns
OTF bytes, or None if nothing usable could be built (caller then falls back to
the guessed web/system family). The cmap is synthesized from glyph PostScript
names via the Adobe Glyph List; symbol/custom-encoded subsets whose names don't
resolve are a known gap for a later pass (we already know their true Unicode
coverage from text extraction — the [[foundation-legs]] char->program map).

No new dependency: fontTools is already used for font identity (see fontid)."""
import io

from fontTools.agl import toUnicode
from fontTools.cffLib import CFFFontSet
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont


def wrap_programs(datas, name):
    """OTF bytes unioning every embedded subset that shares font `name`, or
    None if none can be served."""
    cff_progs, sfnt_best = [], None
    for data in datas:
        if not data:
            continue
        if data[0] == 1 and data[1] == 0:           # CFF header (major=1,minor=0)
            cff_progs.append(data)
        elif data[:4] in (b"\x00\x01\x00\x00", b"true", b"OTTO") \
                or data[:2] == b"tt":               # TrueType / OpenType sfnt
            cand = _read_sfnt(data)
            if cand and (sfnt_best is None
                         or cand[1] > sfnt_best[1]):  # keep the richest subset
                sfnt_best = cand
    try:
        if cff_progs:
            return _build_cff(cff_progs, name)
        if sfnt_best:
            return sfnt_best[0]
    except Exception:
        return None                                  # graceful: fall back
    return None


def _read_sfnt(data):
    """(bytes, glyph_count) for a TrueType/OpenType subset that already has a
    usable Unicode cmap, else None (subset cmaps are often unusable)."""
    try:
        tt = TTFont(io.BytesIO(data), fontNumber=0, lazy=False)
        if "cmap" not in tt or not tt.getBestCmap():
            return None
        buf = io.BytesIO()
        tt.save(buf)
        n = int(tt["maxp"].numGlyphs) if "maxp" in tt else 0
        return buf.getvalue(), n
    except Exception:
        return None


def _build_cff(datas, name):
    """Union the glyphs of every CFF subset of `name` into one OTF + cmap."""
    charstrings, metrics, cmap = {}, {}, {}
    order = [".notdef"]
    upm = 1000
    for data in datas:
        cff = CFFFontSet()
        cff.decompile(io.BytesIO(data), None)
        top = cff[cff.fontNames[0]]
        chars = top.CharStrings
        try:
            fm = top.rawDict.get("FontMatrix")
            if fm and fm[0]:
                upm = int(round(1.0 / fm[0]))
        except Exception:
            pass
        for g in top.getGlyphOrder():
            if g in charstrings:               # same glyph in another subset
                continue
            c = chars[g]
            try:
                c.draw(_NullPen())             # parses the width
            except Exception:
                pass
            width = getattr(c, "width", None)
            if width is None:
                width = upm // 2
            pen = T2CharStringPen(width, None)
            try:
                c.draw(pen)
                charstrings[g] = pen.getCharString()
            except Exception:
                charstrings[g] = T2CharStringPen(width, None).getCharString()
            metrics[g] = (int(width), 0)
            if g != ".notdef":
                order.append(g)
                u = toUnicode(g)               # AGL: 'A'->'A', 'aacute'->'á'
                # ONLY single-char glyphs go in the cmap. Ligatures ('ff','fi',
                # 'ffi'...) expand to multi-char strings that all start with 'f';
                # keying on u[0] would point cmap['f'] at the 'ffi' glyph, so
                # every 'f' would render doubled/tripled. Extracted text is
                # already decomposed (f + i), so we never need the ligature glyph.
                if u and len(u) == 1:
                    cmap[ord(u)] = g
    if ".notdef" not in charstrings:
        charstrings[".notdef"] = T2CharStringPen(upm // 2, None).getCharString()
        metrics[".notdef"] = (upm // 2, 0)
    if not cmap:
        return None

    fb = FontBuilder(upm, isTTF=False)
    fb.setupGlyphOrder(order)
    fb.setupCFF(name, {"FullName": name, "FamilyName": name}, charstrings, {})
    fb.setupCharacterMap(cmap)
    fb.setupHorizontalMetrics(metrics)
    asc, desc = int(upm * 0.8), -int(upm * 0.2)
    fb.setupHorizontalHeader(ascent=asc, descent=desc)
    fb.setupNameTable({"familyName": name, "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=asc, sTypoDescender=desc,
                usWinAscent=asc, usWinDescent=-desc)
    fb.setupPost(keepGlyphNames=False)  # web font needs no glyph names (format 3)
    buf = io.BytesIO()
    fb.font.save(buf)
    return buf.getvalue()


class _NullPen:
    """Consume a charstring's draw calls (we only need the parsed width)."""
    def moveTo(self, *a): pass
    def lineTo(self, *a): pass
    def curveTo(self, *a): pass
    def qCurveTo(self, *a): pass
    def closePath(self): pass
    def endPath(self): pass
    def addComponent(self, *a): pass
