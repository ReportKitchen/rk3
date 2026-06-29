"""Deterministic font identity.

A PDF viewer never guesses whether text is bold — it follows an explicit
reference to a specific embedded font program, and draws that program's glyph
outlines. The "boldness" lives in the outlines themselves. pdfium's text API
flattens distinct programs to one /BaseFont name string, and the programs often
mislabel their own OS/2 weight, so name- and weight-based detection is blind on
exactly the documents that need it.

This module reads the truth instead: it parses each embedded program with
fontTools for its real name / weight / slant, and — when a family's programs all
claim the same weight — ranks them by GLYPH INK (filled outline area per em²),
which separates a bold cut from a regular cut cleanly and deterministically.

Used by extract: every char is tagged with its exact font-program identity
(by spatial match to the text run that drew it), and the font table carries the
resolved weight/italic that analyze's emphasis logic reads directly.
"""
import io
from collections import defaultdict

from fontTools.pens.areaPen import AreaPen
from fontTools.ttLib import TTFont

_INK_TIE = 1.10  # programs within this ink ratio are the same actual weight
_REF_LETTERS = "aeonhsrdmtu"


def _family(name):
    low = (name or "").lower()
    for tok in ("extrablack", "ultrablack", "extrabold", "ultrabold", "semibold",
                "demibold", "extralight", "ultralight", "black", "heavy", "bold",
                "medium", "demi", "semi", "light", "thin", "hairline", "book",
                "regular", "normal", "roman", "italic", "oblique", "cond"):
        low = low.replace(tok, "")
    return "".join(ch for ch in low if ch.isalnum())


def _sample_glyphs(f):
    """Glyph names to measure ink on: common lowercase letters via the cmap, or
    — for CID/CFF subsets without a usable cmap — a spread of the glyph order
    (same-family subsets share glyph names, so the measure stays comparable)."""
    try:
        cmap = f.getBestCmap()
    except Exception:
        cmap = None
    if cmap:
        names = [cmap[ord(c)] for c in _REF_LETTERS if ord(c) in cmap]
        if names:
            return names
    order = [g for g in f.getGlyphOrder() if g != ".notdef"]
    return order[5:21] if len(order) > 25 else order[:16]


def program_props(data, fallback_name="", fallback_weight=400):
    """Parse one embedded font program → {name, weight, italic, ink}. Robust to
    TrueType/CFF/CID and missing cmap/OS-2 (falls back to the values pdfium
    reported). `ink` is {glyph_name: filled_area_per_em2} for same-family
    weight ranking; `italic` may be None when undeterminable here (resolved by
    name downstream)."""
    out = {"name": (fallback_name or "").split("+")[-1],
           "weight": int(fallback_weight or 400), "italic": None, "ink": {}}
    if data:                                  # embedded: read the real program
        try:
            f = TTFont(io.BytesIO(data), fontNumber=0, lazy=True)
            try:
                nm = f["name"]
                out["name"] = (nm.getDebugName(6) or nm.getDebugName(4)
                               or fallback_name).split("+")[-1]
            except Exception:
                pass
            os2 = f.get("OS/2")
            if os2 is not None and getattr(os2, "usWeightClass", None):
                out["weight"] = int(os2.usWeightClass)
                out["italic"] = bool(os2.fsSelection & 0x01)
            post = f.get("post")
            if out["italic"] is None and post is not None and getattr(post, "italicAngle", 0):
                out["italic"] = True
            gs = f.getGlyphSet()
            upm = (f["head"].unitsPerEm if "head" in f else 1000) or 1000
            for gn in _sample_glyphs(f):
                try:
                    pen = AreaPen(gs)
                    gs[gn].draw(pen)
                    out["ink"][gn] = abs(pen.value) / (upm * upm)
                except Exception:
                    pass
        except Exception:
            pass
    if out["italic"] is None:
        # the program's OWN name (or, non-embedded, pdfium's honest base-14 name)
        # is authoritative — reading it is reading the file, not guessing
        low = out["name"].lower()
        out["italic"] = (any(k in low for k in ("italic", "oblique"))
                         or low.endswith(("it", "ita", "obl")))
    return out


def _cluster_by_ink(group):
    """Cluster programs of one family+declared-weight into ACTUAL cuts. Ink is
    measured on ANCHOR glyphs present across the group, so it doesn't drift with
    each subset's glyph repertoire (gates embeds a different subset per page; the
    same regular cut must score the same everywhere). Returns clusters ordered
    light→heavy, or [group] if they can't be told apart."""
    from collections import Counter
    counts = Counter(g for p in group for g in p["ink"])
    anchors = [g for g, c in counts.items() if c >= 0.8 * len(group)]
    if not anchors:
        return [group]

    def aink(p):
        vals = [p["ink"][g] for g in anchors if g in p["ink"]]
        return sum(vals) / len(vals) if vals else 0.0

    ranked = sorted(group, key=aink)
    clusters = [[ranked[0]]]
    for p in ranked[1:]:
        if aink(p) <= aink(clusters[-1][-1]) * _INK_TIE:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return clusters


def resolve_weights(programs):
    """Where a family's metadata can't tell its cuts apart (multiple programs
    declaring the same weight — the mislabelled-bold case), re-rank those
    programs by glyph ink and bump the heavier clusters so emphasis can order
    them. Programs whose declared weights already differ are left untouched."""
    by_family = defaultdict(list)
    for p in programs:
        by_family[_family(p["name"])].append(p)
    for ps in by_family.values():
        if len(ps) < 2:
            continue
        by_weight = defaultdict(list)
        for p in ps:
            by_weight[p["weight"]].append(p)
        for w, group in by_weight.items():
            if len(group) < 2:
                continue
            clusters = _cluster_by_ink(group)
            if len(clusters) < 2:
                continue  # all one actual cut — keep the declared weight
            for k, cluster in enumerate(clusters):
                for p in cluster:
                    p["weight"] = w + k * 100   # heavier cut ranks higher
    return programs
