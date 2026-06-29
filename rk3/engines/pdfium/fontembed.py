"""Build a browser-servable OTF from glyph outlines pdfium extracted directly
from the embedded font program.

The earlier approach wrapped the embedded CFF and synthesized a cmap from the
subset's glyph NAMES — but subsetters sometimes give a glyph a name that doesn't
match its outline, so text rendered with wrong/missing letters. We don't trust
the font's self-description anymore: extract.py reads each glyph's actual outline
via FPDFFont_GetGlyphPath (pdfium resolving the char through the real font) and
keys it by the Unicode the text extraction observed. So the cmap and the shapes
both come from what the PDF actually draws — names, AGL, and the charset are out
of the loop entirely.

No new dependency: fontTools is already used for font identity (see fontid)."""
import io

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen

UPM = 1000  # outlines arrive scaled to this em (see extract._glyph_contours)


def build_from_outlines(glyphs, name):
    """OTF bytes for one font, or None if nothing usable.

    glyphs: {unicode: (advance, contours)} where contours is a list of contours,
    each a list of segments ("m",x,y) / ("l",x,y) / ("c",x1,y1,x2,y2,x3,y3) in
    UPM units (advance too). An empty contour list is a blank glyph (e.g. space).
    """
    if not glyphs:
        return None
    order = [".notdef"]
    charstrings = {".notdef": T2CharStringPen(UPM // 2, None).getCharString()}
    metrics = {".notdef": (UPM // 2, 0)}
    cmap = {}
    for u in sorted(glyphs):
        adv, contours = glyphs[u]
        gname = ("uni%04X" % u) if u <= 0xFFFF else ("u%06X" % u)
        pen = T2CharStringPen(adv, None)
        for contour in contours:
            for seg in contour:
                if seg[0] == "m":
                    pen.moveTo((seg[1], seg[2]))
                elif seg[0] == "l":
                    pen.lineTo((seg[1], seg[2]))
                else:  # cubic bezier
                    pen.curveTo((seg[1], seg[2]), (seg[3], seg[4]),
                                (seg[5], seg[6]))
            pen.closePath()
        charstrings[gname] = pen.getCharString()
        metrics[gname] = (int(adv), 0)
        order.append(gname)
        cmap[u] = gname
    if not cmap:
        return None

    try:
        fb = FontBuilder(UPM, isTTF=False)
        fb.setupGlyphOrder(order)
        fb.setupCFF(name, {"FullName": name, "FamilyName": name},
                    charstrings, {})
        fb.setupCharacterMap(cmap)
        fb.setupHorizontalMetrics(metrics)
        asc, desc = 800, -200
        fb.setupHorizontalHeader(ascent=asc, descent=desc)
        fb.setupNameTable({"familyName": name, "styleName": "Regular"})
        fb.setupOS2(sTypoAscender=asc, sTypoDescender=desc,
                    usWinAscent=asc, usWinDescent=-desc)
        fb.setupPost(keepGlyphNames=False)  # web font needs no glyph names
        buf = io.BytesIO()
        fb.font.save(buf)
        return buf.getvalue()
    except Exception:
        return None  # graceful: this program falls back to the guessed family
