"""Extract stage: per-char text runs (box, font, size, weight, color) and
page PNG renders. The only stage that opens the PDF — page PNGs let analyze
crop figure regions later without re-opening it. Gates on scanned/image PDFs.

Artifact: extract.json
  { "pages": [ { "n": 1-based, "width", "height",
                 "chars": [[unicode_str, l, b, r, t, fontIdx, size, colorIdx], ...] } ],
    "fonts":  [ { "name", "weight", "italic" } ],  # weight/italic = TRUE values
                                                    # (fontid: embedded program + ink rank)
    "colors": [ [r, g, b, a] ] }
Coordinates are PDF points, origin bottom-left.
"""

import ctypes
import hashlib
import math
import re
import statistics
from collections import defaultdict

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from ...pipeline import ScannedPdfError
from . import fontembed, fontid

VERSION = 15


def _matrix_slant_italic(m):
    """Faux italic: a regular font slanted by a SHEAR in the text matrix (the
    renderer leans the upright glyphs). The italic is in the render state, not
    the font — the second deterministic source of slant after the font program.
    True when the baseline stays ~horizontal (so it's a shear, not a rotation)
    and the vertical axis is sheared by a moderate angle."""
    if not m.a or not m.d:
        return False
    baseline_tilt = abs(math.degrees(math.atan2(m.b, m.a)))
    slant = abs(math.degrees(math.atan2(m.c, m.d)))
    return baseline_tilt < 4 and 6 < slant < 35


def _register_program(font_handle, programs, handle_cache):
    """Identify a text run's font by its EMBEDDED PROGRAM (not pdfium's flattened
    /BaseFont name) so distinct cuts sharing a name are kept apart. Returns the
    program's index in `programs`, or None. Cached by font-handle pointer so the
    program data is hashed once, not per text object."""
    addr = ctypes.cast(font_handle, ctypes.c_void_p).value
    if addr in handle_cache:
        return handle_cache[addr]
    nm = ctypes.create_string_buffer(256)
    pdfium_c.FPDFFont_GetBaseFontName(font_handle, nm, 256)
    name = nm.value.decode("utf-8", "replace")
    weight = pdfium_c.FPDFFont_GetWeight(font_handle)
    out_len = ctypes.c_size_t()
    pdfium_c.FPDFFont_GetFontData(font_handle, None, 0, ctypes.byref(out_len))
    size = out_len.value
    if size:
        buf = (ctypes.c_uint8 * size)()
        pdfium_c.FPDFFont_GetFontData(font_handle, buf, size, ctypes.byref(out_len))
        key = hashlib.sha1(bytes(buf)).hexdigest()  # exact program identity
        data = bytes(buf)
    else:                                            # non-embedded (base-14): name is honest
        key = f"noembed:{name}:{weight}"
        data = None
    if key not in programs:
        programs[key] = {"idx": len(programs), "data": data,
                         "name": name, "weight": weight}
    idx = programs[key]["idx"]
    handle_cache[addr] = idx
    return idx


def _text_runs(page_raw, tp_raw, programs, handle_cache):
    """Every text run on the page as (l, b, r, t, program_idx) — the spatial map
    from a char's position to the exact font program that drew it. Bucketed by
    y for fast per-char lookup."""
    runs = []
    for i in range(pdfium_c.FPDFPage_CountObjects(page_raw)):
        o = pdfium_c.FPDFPage_GetObject(page_raw, i)
        if pdfium_c.FPDFPageObj_GetType(o) != pdfium_c.FPDF_PAGEOBJ_TEXT:
            continue
        l, b, r, t = (ctypes.c_float() for _ in range(4))
        if not pdfium_c.FPDFPageObj_GetBounds(
                o, *(ctypes.byref(x) for x in (l, b, r, t))):
            continue
        font_handle = pdfium_c.FPDFTextObj_GetFont(o)
        if not font_handle:
            continue
        idx = _register_program(font_handle, programs, handle_cache)
        runs.append((l.value, b.value, r.value, t.value, idx))
    return runs


def _run_matcher(runs):
    """A lookup: char center (cx, cy) -> program_idx of the smallest text run
    containing it (the run that drew it). Falls back to the nearest run center."""
    BAND = 24.0
    bands = {}
    for run in runs:
        l, b, r, t, _ = run
        for yb in range(int(b // BAND), int(t // BAND) + 1):
            bands.setdefault(yb, []).append(run)

    def match(cx, cy):
        best, best_area = None, None
        for run in bands.get(int(cy // BAND), ()):
            l, b, r, t, idx = run
            if l - 0.5 <= cx <= r + 0.5 and b - 0.5 <= cy <= t + 0.5:
                area = (r - l) * (t - b)
                if best_area is None or area < best_area:
                    best, best_area = idx, area
        return best

    return match

OBJ_PATH, OBJ_IMAGE, OBJ_SHADING = 2, 3, 4

# struct-tree element types that carry meaning for us; everything else
# (Document, Sect, Art, Div, NonStruct…) just passes its role down
SEMANTIC_ROLES = {"Title", "H", "H1", "H2", "H3", "H4", "H5", "H6", "P",
                  "Figure", "Caption", "Table", "TR", "TH", "TD",
                  "L", "LI", "Lbl", "LBody", "TOC", "TOCI", "BlockQuote"}


def _doc_warnings(ctx, pdf):
    """Doc-level advisories for layout classes we knowingly convert best-effort
    rather than refuse. Surfaced as a banner (not a hard bail like the scanned
    gate) so the user knows the issues are recognised, not missed."""
    warnings = []
    try:
        md = pdf.get_metadata_dict()
    except Exception:
        md = {}
    producer = md.get("Producer") or ""
    creator = md.get("Creator") or ""
    blob = f"{producer} {creator}".lower()
    if ("skia/pdf" in blob or "headlesschrome" in blob or "wkhtmltopdf" in blob
            or "chromium" in blob or "puppeteer" in blob
            or "mozilla/" in creator.lower()):
        warnings.append({
            "code": "web-print",
            "title": "Generated by a browser/app export",
            "detail": (
                f"This PDF came from a browser or app export "
                f"(“{(producer or creator)[:60]}”) rather than a page-layout "
                "tool. These can be very cleanly built, but they tend to flow "
                "tables and lists across page boundaries in ways designed "
                "documents don’t — so double-check multi-page tables and lists."),
        })
    for w in warnings:
        ctx.log.entry("doc-warning", code=w["code"], title=w["title"],
                      producer=producer, creator=creator[:80])
    return warnings


def run(ctx):
    cfg_in = ctx.cfg["input"]
    pdf = pdfium.PdfDocument(ctx.source)
    try:
        warnings = _doc_warnings(ctx, pdf)
        n_pages = len(pdf)
        page_range = cfg_in.get("pageRange") or [1, n_pages]
        first, last = max(1, page_range[0]), min(n_pages, page_range[1])

        programs, handle_cache = {}, {}   # font-program identity (see _register_program)
        slant_chars = []                  # chars faux-italicised by a matrix shear
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

            # map char position -> the font program that drew it (deterministic)
            match_font = _run_matcher(_text_runs(page.raw, tp.raw, programs, handle_cache))
            last_fidx = 0

            chars = []
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
                slant_italic = False
                if pdfium_c.FPDFText_GetMatrix(tp, i, ctypes.byref(matrix)):
                    size *= (matrix.b ** 2 + matrix.d ** 2) ** 0.5
                    slant_italic = _matrix_slant_italic(matrix)
                size = round(size, 2)

                # font = the exact embedded program at this char's position;
                # a synthetic char (pdfium-inserted space) inherits its neighbour
                fidx = match_font((l + r) / 2, (b + t) / 2)
                if fidx is None:
                    fidx = last_fidx
                last_fidx = fidx

                cr, cg, cb, ca = (ctypes.c_uint() for _ in range(4))
                ok = pdfium_c.FPDFText_GetFillColor(
                    tp, i, ctypes.byref(cr), ctypes.byref(cg),
                    ctypes.byref(cb), ctypes.byref(ca))
                ckey = (cr.value, cg.value, cb.value, ca.value) if ok else (0, 0, 0, 255)

                # GetUnicode yields UTF-16 code units: non-BMP characters
                # arrive as a surrogate pair across two indices - recombine
                # (union the charboxes), drop unpaired halves
                ch = [chr(uc), round(l, 2), round(b, 2), round(r, 2),
                      round(t, 2), fidx, size, color_id(ckey)]
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
                if slant_italic:
                    slant_chars.append(ch)

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

        # resolve every distinct font program to its TRUE weight/slant: read the
        # embedded program with fontTools, then rank same-family cuts the PDF
        # mislabelled by glyph ink (see fontid). This weight/italic is what
        # analyze's emphasis logic reads — no name-token or width guessing.
        props = [None] * len(programs)
        for p in programs.values():
            props[p["idx"]] = fontid.program_props(p["data"], p["name"], p["weight"])
        fontid.resolve_weights(props)
        fonts = [{"name": pr["name"], "weight": pr["weight"],
                  "italic": bool(pr["italic"])} for pr in props]
        # faux italic (matrix shear on an upright program): give each such run a
        # synthetic italic variant of its program, so per-char fontIdx -> italic
        # keeps working — the second deterministic source of slant, read not guessed
        slant_of = {}
        for ch in slant_chars:
            base = ch[5]
            if base not in slant_of:
                b = fonts[base]
                slant_of[base] = len(fonts)
                fonts.append({"name": b["name"], "weight": b["weight"], "italic": True})
            ch[5] = slant_of[base]
        ctx.log.entry("fonts", count=len(fonts), faux_italic=len(slant_of),
                      fonts=[(f["name"][:24], f["weight"], f["italic"]) for f in fonts][:24])

        # embedded font assets for the optional "use the PDF's fonts" mode:
        # union every per-page subset that shares a name into one browser OTF
        # (render emits @font-face when output.embedFonts is on). Always built
        # (cheap) so toggling the flag is a render-only reconvert; a program we
        # can't wrap is simply omitted and falls back to the guessed family.
        groups = defaultdict(lambda: {"datas": [], "weight": 400, "italic": False})
        for p in programs.values():
            pr = props[p["idx"]]
            g = groups[pr["name"]]
            g["datas"].append(p["data"])
            g["weight"], g["italic"] = pr["weight"], bool(pr["italic"])
        embedded = {}
        for nm, g in groups.items():
            otf = fontembed.wrap_programs(g["datas"], nm)
            if not otf:
                continue
            safe = re.sub(r"[^A-Za-z0-9_-]", "_", nm) or "font"
            (ctx.outdir / "fonts").mkdir(exist_ok=True)
            (ctx.outdir / "fonts" / f"{safe}.otf").write_bytes(otf)
            # render groups cuts into one CSS family (e.g. all Gotham cuts ->
            # "PDFEmbed Gotham") so <strong>/<em> pick the bold/italic FACE by
            # weight/style — so the manifest just needs the file + true cut
            embedded[nm] = {"file": f"fonts/{safe}.otf",
                            "weight": g["weight"], "italic": g["italic"]}
        ctx.log.entry("embed-fonts", served=len(embedded), of=len(groups))

        ctx.write_artifact("extract", {
            "pages": pages_out, "fonts": fonts, "colors": colors,
            "warnings": warnings, "embeddedFonts": embedded,
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
