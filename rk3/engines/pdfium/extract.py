"""Extract stage: per-char text runs (box, font, size, weight, color) and
page PNG renders. The only stage that opens the PDF — page PNGs let analyze
crop figure regions later without re-opening it. Gates on scanned/image PDFs.

Artifact: extract.json
  { "pages": [ { "n": 1-based, "width", "height",
                 "chars": [[unicode_str, l, b, r, t, fontIdx, size, colorIdx], ...] } ],
    "fonts":  [ { "name", "weight", "flags" } ],
    "colors": [ [r, g, b, a] ] }
Coordinates are PDF points, origin bottom-left.
"""

import ctypes
import statistics

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from ...pipeline import ScannedPdfError

VERSION = 8

OBJ_PATH, OBJ_IMAGE, OBJ_SHADING = 2, 3, 4

# struct-tree element types that carry meaning for us; everything else
# (Document, Sect, Art, Div, NonStruct…) just passes its role down
SEMANTIC_ROLES = {"Title", "H", "H1", "H2", "H3", "H4", "H5", "H6", "P",
                  "Figure", "Caption", "Table", "TR", "TH", "TD",
                  "L", "LI", "Lbl", "LBody", "TOC", "TOCI", "BlockQuote"}


def run(ctx):
    cfg_in = ctx.cfg["input"]
    pdf = pdfium.PdfDocument(ctx.source)
    try:
        n_pages = len(pdf)
        page_range = cfg_in.get("pageRange") or [1, n_pages]
        first, last = max(1, page_range[0]), min(n_pages, page_range[1])

        fonts, font_index = [], {}
        colors, color_index = [], {}
        pages_out = []
        char_counts = []

        def color_id(rgba) -> int:
            if rgba not in color_index:
                color_index[rgba] = len(colors)
                colors.append(list(rgba))
            return color_index[rgba]

        pages_dir = ctx.outdir / "pages"
        pages_dir.mkdir(exist_ok=True)
        scale = cfg_in.get("pageImageScale", 2)

        for pno in range(first - 1, last):
            page = pdf[pno]
            tp = page.get_textpage()
            n_chars = tp.count_chars()
            char_counts.append(n_chars)

            chars = []
            buf = ctypes.create_string_buffer(512)
            matrix = pdfium_c.FS_MATRIX()
            pending = None  # high surrogate awaiting its low half
            for i in range(n_chars):
                uc = pdfium_c.FPDFText_GetUnicode(tp, i)
                if uc == 0:
                    continue
                l, b, r, t = tp.get_charbox(i)
                # nominal font size is often 1.0 with the real size in the text
                # matrix (InDesign/Quartz), so fold the matrix scale in
                size = pdfium_c.FPDFText_GetFontSize(tp, i)
                if pdfium_c.FPDFText_GetMatrix(tp, i, ctypes.byref(matrix)):
                    size *= (matrix.b ** 2 + matrix.d ** 2) ** 0.5
                size = round(size, 2)

                flags = ctypes.c_int(0)
                nlen = pdfium_c.FPDFText_GetFontInfo(
                    tp, i, buf, len(buf), ctypes.byref(flags))
                name = buf.raw[: max(0, nlen - 1)].decode("utf-8", "replace") if nlen > 1 else ""
                weight = pdfium_c.FPDFText_GetFontWeight(tp, i)
                fkey = (name, weight, flags.value)
                if fkey not in font_index:
                    font_index[fkey] = len(fonts)
                    fonts.append({"name": name, "weight": weight, "flags": flags.value})

                cr, cg, cb, ca = (ctypes.c_uint() for _ in range(4))
                ok = pdfium_c.FPDFText_GetFillColor(
                    tp, i, ctypes.byref(cr), ctypes.byref(cg),
                    ctypes.byref(cb), ctypes.byref(ca))
                ckey = (cr.value, cg.value, cb.value, ca.value) if ok else (0, 0, 0, 255)

                # GetUnicode yields UTF-16 code units: non-BMP characters
                # arrive as a surrogate pair across two indices - recombine
                # (union the charboxes), drop unpaired halves
                ch = [chr(uc), round(l, 2), round(b, 2), round(r, 2),
                      round(t, 2), font_index[fkey], size, color_id(ckey)]
                if 0xD800 <= uc <= 0xDBFF:
                    pending = ch
                    continue
                if 0xDC00 <= uc <= 0xDFFF:
                    if pending is not None:
                        cp = (0x10000 + ((ord(pending[0]) - 0xD800) << 10)
                              + (uc - 0xDC00))
                        chars.append([chr(cp), min(pending[1], ch[1]),
                                      min(pending[2], ch[2]),
                                      max(pending[3], ch[3]),
                                      max(pending[4], ch[4]),
                                      pending[5], pending[6], pending[7]])
                    pending = None
                    continue
                pending = None
                chars.append(ch)

            pages_out.append({
                "n": pno + 1,
                "width": round(page.get_width(), 2),
                "height": round(page.get_height(), 2),
                "chars": chars,
                "objects": _page_objects(page, color_id),
                "links": _page_links(pdf, page),
                "tagged": _tagged_regions(page),
            })

            bitmap = page.render(scale=scale)
            bitmap.to_pil().save(pages_dir / f"page-{pno + 1:04d}.png")
            ctx.log.entry("page", page=pno + 1, chars=n_chars,
                          image=f"pages/page-{pno + 1:04d}.png")
            tp.close()
            page.close()

        threshold = cfg_in.get("scannedTextThreshold", 100)
        median_chars = statistics.median(char_counts) if char_counts else 0
        if median_chars < threshold:
            ctx.log.entry("scanned-gate", median_chars=median_chars,
                          threshold=threshold, result="bail")
            raise ScannedPdfError(
                f"Scanned/image PDF (median {median_chars:.0f} extractable chars/page, "
                f"threshold {threshold}) — OCR is out of scope.")

        ctx.write_artifact("extract", {
            "pages": pages_out, "fonts": fonts, "colors": colors,
        })
    finally:
        pdf.close()


def _page_objects(page, color_id):
    """Graphic page objects (paths/images/shadings) for figure & callout
    detection downstream:
    [type, l, b, r, t, fillIdx, strokeIdx, filled, stroked,
     strokeWidth, segments]
    segments (stroked simple paths only): [[x, y, segType, close], ...] in
    page space — lets analyze tell a left+bottom accent border from a full
    box outline."""
    objects = []
    for obj in page.get_objects(max_depth=2):
        if obj.type not in (OBJ_PATH, OBJ_IMAGE, OBJ_SHADING):
            continue
        try:
            l, b, r, t = obj.get_bounds()
        except Exception:
            continue
        fill = stroke = None
        filled = stroked = 0
        stroke_w = None
        segs = None
        if obj.type == OBJ_PATH:
            c = [ctypes.c_uint() for _ in range(4)]
            if pdfium_c.FPDFPageObj_GetFillColor(obj.raw, *map(ctypes.byref, c)):
                fill = color_id(tuple(x.value for x in c))
            if pdfium_c.FPDFPageObj_GetStrokeColor(obj.raw, *map(ctypes.byref, c)):
                stroke = color_id(tuple(x.value for x in c))
            fmode, smode = ctypes.c_int(), ctypes.c_int()
            if pdfium_c.FPDFPath_GetDrawMode(obj.raw, ctypes.byref(fmode),
                                             ctypes.byref(smode)):
                filled, stroked = int(fmode.value != 0), int(smode.value != 0)
            if stroked:
                w = ctypes.c_float()
                if pdfium_c.FPDFPageObj_GetStrokeWidth(obj.raw, ctypes.byref(w)):
                    stroke_w = round(w.value, 2)
                segs = _path_segments(obj)
        objects.append([obj.type, round(l, 2), round(b, 2), round(r, 2),
                        round(t, 2), fill, stroke, filled, stroked,
                        stroke_w, segs])
    return objects


def _path_segments(obj, max_segs=10):
    """Page-space points of a simple path (None when complex)."""
    n = pdfium_c.FPDFPath_CountSegments(obj.raw)
    if not 0 < n <= max_segs:
        return None
    m = pdfium_c.FS_MATRIX()
    if not pdfium_c.FPDFPageObj_GetMatrix(obj.raw, ctypes.byref(m)):
        m.a, m.b, m.c, m.d, m.e, m.f = 1, 0, 0, 1, 0, 0
    segs = []
    for i in range(n):
        seg = pdfium_c.FPDFPath_GetPathSegment(obj.raw, i)
        x, y = ctypes.c_float(), ctypes.c_float()
        if not pdfium_c.FPDFPathSegment_GetPoint(seg, ctypes.byref(x),
                                                 ctypes.byref(y)):
            return None
        px = m.a * x.value + m.c * y.value + m.e
        py = m.b * x.value + m.d * y.value + m.f
        segs.append([round(px, 1), round(py, 1),
                     pdfium_c.FPDFPathSegment_GetType(seg),
                     int(bool(pdfium_c.FPDFPathSegment_GetClose(seg)))])
    return segs


def _tagged_regions(page):
    """For tagged PDFs: regions of the page with a structure-tree role,
    [[l, b, r, t, role], ...]. Built by joining the struct tree (role per
    marked-content id) with page-object content marks (MCID + bounds).
    Decorations marked Artifact in the content stream get role "Artifact"
    even though they have no struct element. Empty list for untagged pages."""
    roles = _struct_roles(page)
    regions = []
    for obj in page.get_objects(max_depth=2):
        mcid, artifact = _object_mark(obj)
        role = "Artifact" if artifact else roles.get(mcid)
        if role is None:
            continue
        try:
            l, b, r, t = obj.get_bounds()
        except Exception:
            continue
        if r - l <= 0 or t - b <= 0:
            continue
        regions.append([round(l, 2), round(b, 2), round(r, 2), round(t, 2), role])
    return regions


def _struct_roles(page):
    """mcid -> nearest semantic ancestor role, from the page's struct tree."""
    roles = {}
    st = pdfium_c.FPDF_StructTree_GetForPage(page)
    if not st:
        return roles

    buf = ctypes.create_string_buffer(128)

    def walk(elem, inherited):
        n = pdfium_c.FPDF_StructElement_GetType(elem, buf, len(buf))
        etype = buf.raw[:max(0, n - 2)].decode("utf-16-le", "replace") if n > 2 else ""
        role = etype if etype in SEMANTIC_ROLES else inherited
        if role:
            cnt = pdfium_c.FPDF_StructElement_GetMarkedContentIdCount(elem)
            for i in range(max(0, cnt)):
                mid = pdfium_c.FPDF_StructElement_GetMarkedContentIdAtIndex(elem, i)
                if mid >= 0:
                    roles[mid] = role
        for i in range(pdfium_c.FPDF_StructElement_CountChildren(elem)):
            child = pdfium_c.FPDF_StructElement_GetChildAtIndex(elem, i)
            if child:
                walk(child, role)

    try:
        for i in range(pdfium_c.FPDF_StructTree_CountChildren(st)):
            walk(pdfium_c.FPDF_StructTree_GetChildAtIndex(st, i), None)
    finally:
        pdfium_c.FPDF_StructTree_Close(st)
    return roles


def _object_mark(obj):
    """(mcid, is_artifact) from a page object's content marks."""
    for i in range(pdfium_c.FPDFPageObj_CountMarks(obj.raw)):
        mark = pdfium_c.FPDFPageObj_GetMark(obj.raw, i)
        wbuf = (ctypes.c_ushort * 64)()
        blen = ctypes.c_ulong(0)
        pdfium_c.FPDFPageObjMark_GetName(mark, wbuf, ctypes.sizeof(wbuf),
                                         ctypes.byref(blen))
        name = bytes(wbuf)[:max(0, blen.value - 2)].decode("utf-16-le", "replace")
        if name == "Artifact":
            return None, True
        mcid = ctypes.c_int(-1)
        if pdfium_c.FPDFPageObjMark_GetParamIntValue(mark, b"MCID",
                                                     ctypes.byref(mcid)):
            return mcid.value, False
    return None, False


def _page_links(pdf, page):
    """Link annotations: [l, b, r, t, target] where target is
    {"uri": ...} or {"destPage": 1-based} (or both null fields absent)."""
    links = []
    for i in range(pdfium_c.FPDFPage_GetAnnotCount(page)):
        annot = pdfium_c.FPDFPage_GetAnnot(page, i)
        try:
            if pdfium_c.FPDFAnnot_GetSubtype(annot) != pdfium_c.FPDF_ANNOT_LINK:
                continue
            rect = pdfium_c.FS_RECTF()
            if not pdfium_c.FPDFAnnot_GetRect(annot, ctypes.byref(rect)):
                continue
            link = pdfium_c.FPDFAnnot_GetLink(annot)
            if not link:
                continue
            target = {}
            action = pdfium_c.FPDFLink_GetAction(link)
            if action and pdfium_c.FPDFAction_GetType(action) == pdfium_c.PDFACTION_URI:
                n = pdfium_c.FPDFAction_GetURIPath(pdf.raw, action, None, 0)
                buf = ctypes.create_string_buffer(n)
                pdfium_c.FPDFAction_GetURIPath(pdf.raw, action, buf, n)
                target["uri"] = buf.value.decode("utf-8", "replace")
            else:
                dest = pdfium_c.FPDFLink_GetDest(pdf.raw, link)
                if dest:
                    target["destPage"] = pdfium_c.FPDFDest_GetDestPageIndex(pdf.raw, dest) + 1
            if target:
                # FS_RECTF top/bottom are not reliably ordered for annots;
                # normalize so b <= t and l <= r
                ys = sorted((rect.bottom, rect.top))
                xs = sorted((rect.left, rect.right))
                links.append([round(xs[0], 2), round(ys[0], 2),
                              round(xs[1], 2), round(ys[1], 2), target])
        finally:
            pdfium_c.FPDFPage_CloseAnnot(annot)
    return links
