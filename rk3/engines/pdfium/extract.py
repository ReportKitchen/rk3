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

VERSION = 3

OBJ_PATH, OBJ_IMAGE, OBJ_SHADING = 2, 3, 4


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

                chars.append([chr(uc), round(l, 2), round(b, 2), round(r, 2),
                              round(t, 2), font_index[fkey], size, color_id(ckey)])

            pages_out.append({
                "n": pno + 1,
                "width": round(page.get_width(), 2),
                "height": round(page.get_height(), 2),
                "chars": chars,
                "objects": _page_objects(page, color_id),
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
    detection downstream: [type, l, b, r, t, fillIdx, strokeIdx, filled, stroked]."""
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
        objects.append([obj.type, round(l, 2), round(b, 2), round(r, 2),
                        round(t, 2), fill, stroke, filled, stroked])
    return objects
