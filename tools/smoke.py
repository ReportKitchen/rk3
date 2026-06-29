#!/usr/bin/env python3
"""Content-conversion smoke tests — cheap, high-precision red flags run against
a converted document's IR (output/pdfium/<slug>/ir.json).

These are review aids, not pipeline code. They encode three of Nathan's
field-tested intuitions about what a *correct* conversion looks like:

  A. ORPHAN BULLET  — a bullet glyph (●○•▪…) sitting inside paragraph text is
     almost always a list that didn't get detected. A real <li> strips its
     marker, so a surviving bullet glyph in prose == missed UL.

  B. BROKEN PARAGRAPH — ordinary prose almost never starts with a lowercase
     letter, and almost never ends without terminal punctuation. A paragraph
     that ends mid-sentence followed by one that starts lowercase is one
     paragraph that got split (bad line/column join, footnote intrusion, etc.).

Both are gated by `is_normal_paragraph()` — a general "does this <p> look like
real prose" heuristic — so we don't cry wolf on headings, captions, labels,
all-caps banners, citation lists, or deliberate hard-return blocks.

Usage:
  python tools/smoke.py <slug>          # one doc
  python tools/smoke.py --all           # every converted doc
  python tools/smoke.py <slug> --page 9 # filter to a page
"""
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output" / "pdfium"

# Glyphs that are bullets, period. Deliberately excludes -, –, —, *, · (ambiguous
# in prose) to keep precision high. These never legitimately sit inside a sentence.
BULLET_GLYPHS = "●○•▪◦‣■□▸▶►◆◇♦❖✦➤❯"
BULLET_RE = re.compile("[" + re.escape(BULLET_GLYPHS) + "]")

# "Crazy symbols" that disqualify a block from being normal prose.
WEIRD_RE = re.compile("[" + re.escape(BULLET_GLYPHS + "|►▶◀▼") + "]")

TERMINAL = ".!?…"
CLOSERS = "\"'’”»)]}"  # may trail the terminal punctuation


def _strip_closers(s):
    """Drop trailing quotes/brackets and a trailing footnote-ref digit so the
    real sentence terminator is exposed."""
    s = s.rstrip()
    # trailing footnote marker: a digit (or two) hanging off the end of a sentence
    s = re.sub(r"(?<=[.!?…])\s*\d{1,3}$", lambda m: m.group(0)[0], s)
    while s and s[-1] in CLOSERS:
        s = s[:-1].rstrip()
    return s


def _first_alpha(s):
    for ch in s.strip():
        if ch.isalpha():
            return ch
        if ch.isdigit():
            return None  # leads with a number — not a lowercase-start signal
        # skip opening quotes/brackets/spaces
        if ch in "\"'‘“([{":
            continue
        return None
    return None


def classify(text):
    """Signals for one block of text."""
    t = (text or "").strip()
    words = t.split()
    wc = len(words)
    letters = [c for c in t if c.isalpha()]
    all_caps = bool(letters) and all(c.isupper() for c in letters)
    first = _first_alpha(t)
    starts_lower = first is not None and first.islower()
    starts_cap = first is not None and first.isupper()
    core = _strip_closers(t)
    ends_terminal = bool(core) and core[-1] in TERMINAL
    has_sentence_punct = any(p in t for p in ".!?")
    has_bullet = bool(BULLET_RE.search(t))
    weird = bool(WEIRD_RE.search(t))
    return {
        "wc": wc,
        "all_caps": all_caps,
        "starts_lower": starts_lower,
        "starts_cap": starts_cap,
        "ends_terminal": ends_terminal,
        "has_sentence_punct": has_sentence_punct,
        "has_bullet": has_bullet,
        "weird": weird,
    }


def is_normal_paragraph(text):
    """True when `text` reads like an ordinary prose paragraph: several words,
    real sentence punctuation, starts capital, ends terminal, not all-caps, no
    weird symbols. Used to suppress false positives — only *normal-looking*
    paragraphs are held to the start/end rules below."""
    c = classify(text)
    return (
        c["wc"] >= 5
        and c["has_sentence_punct"]
        and c["starts_cap"]
        and c["ends_terminal"]
        and not c["all_caps"]
        and not c["weird"]
    )


def is_prose_candidate(text):
    """Looser gate: enough words, has a period, not all-caps, no bullet. Used to
    decide a block is prose *enough* that a lowercase start / missing terminator
    is suspicious rather than expected."""
    c = classify(text)
    return c["wc"] >= 5 and c["has_sentence_punct"] and not c["all_caps"] and not c["has_bullet"]


def _excerpt(t, n=90):
    t = " ".join((t or "").split())
    return t if len(t) <= n else t[:n] + "…"


def scan(slug, page_filter=None):
    irp = OUT / slug / "ir.json"
    if not irp.exists():
        return None
    body = json.load(open(irp))["body"]
    flags = []  # (page, kind, nid, message, excerpt)

    paras = [n for n in body if isinstance(n, dict)]
    for i, n in enumerate(paras):
        typ = n.get("type")
        page = n.get("page")
        nid = n.get("nid")
        text = n.get("text", "")

        # ---- A. orphan bullet inside non-list prose ----
        if typ in ("paragraph", "heading", "aside") and text and BULLET_RE.search(text):
            segs = [s.strip() for s in BULLET_RE.split(text) if s.strip()]
            glyph = BULLET_RE.search(text).group(0)
            leading = bool(BULLET_RE.match(text.strip()))
            # Separator case: a row of short labels joined by bullets (datelines,
            # contact rows: "email • phone • address") — NOT a list. Heuristic:
            # several segments, every one short, none ends with sentence punct.
            sep = (len(segs) >= 2 and not leading
                   and all(len(s.split()) <= 5 for s in segs)
                   and not any(s.rstrip()[-1:] in TERMINAL for s in segs))
            if sep:
                flags.append((page, "BULLET-SEP?", nid,
                              f"inline '{glyph}' separators between short labels — dateline/contact row, not a list",
                              _excerpt(text)))
            else:
                where = "leading" if leading else "mid-paragraph"
                flags.append((page, "ORPHAN-BULLET", nid,
                              f"{where} '{glyph}' in <{typ}> — almost certainly a missed list",
                              _excerpt(text)))

        # ---- B. broken paragraph ----
        if typ == "paragraph" and text:
            c = classify(text)
            # B1: normal-looking prose that starts lowercase = split continuation
            if c["starts_lower"] and is_prose_candidate(text):
                flags.append((page, "BROKEN-START", nid,
                              "prose paragraph starts lowercase — likely split from the block before it",
                              _excerpt(text)))
            # B2: prose paragraph that doesn't end terminal, followed by a
            # lowercase-starting paragraph = one paragraph cut in two.
            if is_prose_candidate(text) and not c["ends_terminal"]:
                nxt = paras[i + 1] if i + 1 < len(paras) else None
                if (nxt and nxt.get("type") == "paragraph"
                        and classify(nxt.get("text", ""))["starts_lower"]):
                    flags.append((page, "BROKEN-PAIR", nid,
                                  f"no terminal punctuation; next <p> ({nxt.get('nid')}) starts lowercase — one paragraph split in two",
                                  _excerpt(text) + "  ⟶  " + _excerpt(nxt.get("text", ""), 50)))

    if page_filter is not None:
        flags = [f for f in flags if f[0] == page_filter]
    return flags


def report(slug, page_filter=None):
    flags = scan(slug, page_filter)
    if flags is None:
        print(f"  (no ir.json for {slug})")
        return 0
    from collections import Counter
    counts = Counter(f[1] for f in flags)
    head = f"{slug}  —  {len(flags)} flags  " + " ".join(f"{k}:{v}" for k, v in counts.items())
    print(head)
    for page, kind, nid, msg, ex in sorted(flags, key=lambda f: (f[0] or 0)):
        print(f"  p{page:<3} {kind:<13} {nid}  {msg}")
        print(f"       “{ex}”")
    return len(flags)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    page = None
    if "--page" in argv:
        page = int(argv[argv.index("--page") + 1])
    if "--all" in argv:
        total = 0
        for d in sorted(OUT.iterdir()):
            if (d / "ir.json").exists():
                total += report(d.name)
                print()
        print(f"TOTAL: {total} flags across all docs")
        return
    if not args:
        print(__doc__)
        return
    report(args[0], page)


if __name__ == "__main__":
    main(sys.argv[1:])
