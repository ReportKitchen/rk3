"""Read-only TOC ⇔ headings reconciliation (no pipeline change).

Recovers the table-of-contents blocks that analyze detected and dropped (logged
as toc-drop / toc-tag-drop), parses each line into an outline entry
{title, level, page}, then matches those against the heading nodes in the IR and
reports per-entry notes: match / level? / missed, plus headings that aren't in
the TOC (extras — usually legitimately below TOC depth).

This is a diagnostic only: it reads existing artifacts (blocks.json,
debug-analyze.jsonl, ir.json) and never writes or re-runs anything. If the
parsing proves good it can later move into analyze as ir["outline"].
"""

import json
import re
from collections import Counter

from rk3.documents import output_dir


def _median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

# trailing printed page number: arabic after optional leaders ("Title .... 18"),
# OR a roman numeral but ONLY after real dot leaders, so it can't swallow a word
# that happens to end in roman letters ("…civil", "…mix")
_PAGE_TAIL = re.compile(
    r"(?:[\s.·•…\-—_]*\b(\d{1,4})|[.·•…]{2,}\s*\b([ivxlcdm]{1,7}))\s*$", re.I)
# leading decimal section number "1", "1.2", "3.4.1"
_SEC_NUM = re.compile(r"^((?:\d+\.)*\d+)\.?\s+")
# chapter/part/appendix keyword openers (treated as top level)
_CHAPTER = re.compile(r"^(chapter|part|section|appendix)\s+[0-9ivxlc]+\b[:.]?\s*", re.I)


def _norm(t):
    """Title comparison key: lowercase, strip leading section number / chapter
    keyword, drop punctuation, collapse whitespace."""
    t = t.lower()
    t = _SEC_NUM.sub("", t)
    t = _CHAPTER.sub("", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _toc_blocks(od):
    """The TOC blocks analyze dropped, recovered from blocks.json by rk."""
    blocks = json.loads((od / "blocks.json").read_text())["blocks"]
    by_rk = {b.get("rk"): b for b in blocks}
    rks, seen = [], set()
    dbg = od / "debug-analyze.jsonl"
    if dbg.exists():
        for line in dbg.read_text().splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("event") in ("toc-drop", "toc-tag-drop"):
                rk = e.get("block")
                if rk and rk not in seen:
                    seen.add(rk)
                    rks.append(rk)
    return [by_rk[rk] for rk in rks if rk in by_rk]


_ONLY_NUM = re.compile(r"0?\d{1,3}$")
_LEAD_NUM = re.compile(r"^\s*(0?\d{1,3})\s+(.+)")
_DOT_TAIL = re.compile(r"(\s*[.·•…]){2,}\s*$")
_DASH_LEAD = re.compile(r"^[\s.·•…\-–—_]+")


def _parse_toc(blocks):
    """One outline entry per TOC line: {title, level, page, x, norm}. Handles the
    designed-TOC layouts too: a page number can be TRAILING ("Title … 18"),
    LEADING ("18 Title"), or in a SEPARATE aligned column paired to the entry by
    baseline. Lowercase-starting lines are wraps of the previous entry."""
    # flatten every TOC line with its geometry, top-to-bottom
    raws = []
    for b in blocks:
        for ln in b.get("lines", []):
            t = ln["text"].strip()
            if t:
                raws.append({"t": t, "x": ln["bbox"][0],
                             "ymid": (ln["bbox"][1] + ln["bbox"][3]) / 2})
    raws.sort(key=lambda r: -r["ymid"])
    # standalone page-number blocks (the number column) — paired to entries by y
    numbers = [r for r in raws if _ONLY_NUM.fullmatch(r["t"])]

    def pair_number(entry):
        best, bestd = None, 6.0
        for n in numbers:
            if not n.get("used") and abs(n["ymid"] - entry["ymid"]) < bestd:
                bestd, best = abs(n["ymid"] - entry["ymid"]), n
        if best is not None:
            best["used"] = True
            return best["t"]
        return None

    entries = []
    for r in raws:
        raw = r["t"]
        if _ONLY_NUM.fullmatch(raw):
            continue  # the number column itself; paired below
        page, body = None, raw
        lead = _LEAD_NUM.match(raw)
        tail = _PAGE_TAIL.search(raw)
        if lead and lead.group(2)[:1].isalpha() and lead.group(2)[:1].isupper():
            page, body = lead.group(1), lead.group(2).strip()   # "18 Title"
        elif tail:
            page, body = (tail.group(1) or tail.group(2)), raw[:tail.start()].strip()
        body = _DASH_LEAD.sub("", _DOT_TAIL.sub("", body)).strip()
        first = next((c for c in body if c.isalpha()), "")
        if entries and first and first.islower():
            e = entries[-1]                          # line wrap: fold into previous
            e["title"] = f"{e['title']} {body}".strip()
            if e["page"] is None:
                e["page"] = page
            e["norm"] = _norm(e["title"])
            continue
        n = _norm(body)
        if len(n) < 2 or n in ("contents", "table of contents"):
            continue
        if page is None:                             # separate number column
            page = pair_number(r)
        entries.append({"title": body, "level": None, "page": page,
                        "x": r["x"], "norm": n})
    _assign_levels(entries)
    return entries


def _assign_levels(entries):
    """Level per entry. Most TOCs INDENT nested entries, so cluster the left
    edges into tiers and read level off the tier — this catches un-numbered
    sub-entries ('Stage 1', 'What the Science Says') that numbering misses. If
    the TOC is flat (one tier), fall back to decimal section-number depth."""
    if not entries:
        return
    reps = []                                        # indent-tier left edges
    for x in sorted({round(e["x"], 1) for e in entries}):
        if not reps or x - reps[-1] > 8:
            reps.append(x)
    use_x = len(reps) >= 2 and reps[-1] - reps[0] >= 8
    for e in entries:
        if use_x:
            lvl = 1
            for i, r in enumerate(reps):
                if e["x"] >= r - 4:
                    lvl = i + 1
            e["level"] = min(lvl, 6)
        elif _CHAPTER.match(e["title"]):
            e["level"] = 1
        else:
            sm = _SEC_NUM.match(e["title"])
            e["level"] = sm.group(1).count(".") + 1 if sm else None


def _headings(od):
    ir = json.loads((od / "ir.json").read_text())
    out = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("type") == "heading":
                num = n.get("sectionNum")
                full = (f"{num} {n.get('text', '')}".strip() if num
                        else n.get("text", ""))
                out.append({"text": full, "level": n.get("level"),
                            "page": n.get("page"), "nid": n.get("nid"),
                            "norm": _norm(full)})
            for k in ("body", "children", "content"):
                if k in n:
                    walk(n[k])
        elif isinstance(n, list):
            for x in n:
                walk(x)

    walk(ir)
    return out


def _title_match(e, h):
    if not (e["norm"] and h["norm"]):
        return False
    if e["norm"] == h["norm"]:
        return True
    return (min(len(e["norm"]), len(h["norm"])) >= 6
            and (e["norm"] in h["norm"] or h["norm"] in e["norm"]))


def _arabic(p):
    try:
        return int(p)
    except (TypeError, ValueError):
        return None  # roman numeral / None


def _reconcile(toc, heads):
    """Match TOC entries to headings, then emit one unified list in OUR document
    order: every detected heading is a row (with its TOC counterpart, or blank
    when it's below TOC depth); unmatched TOC entries interleave as 'missed'.

    A title can legitimately repeat — an executive summary often mirrors the
    chapter list — but the TOC is in PAGE ORDER. So rather than grab the first
    title match (which would steal the exec-summary mention and leave the real
    chapter blank), estimate the printed→physical page offset from confident 1:1
    matches, then map each TOC entry to the occurrence nearest its expected
    page. Falls back to order-preserving first-match when pages aren't usable."""
    cand = {ti: [hi for hi, h in enumerate(heads) if _title_match(e, h)]
            for ti, e in enumerate(toc)}
    head_uses = Counter(hi for hs in cand.values() for hi in hs)
    offs = [heads[hs[0]]["page"] - _arabic(toc[ti]["page"])
            for ti, hs in cand.items()
            if _arabic(toc[ti]["page"]) and len(hs) == 1
            and head_uses[hs[0]] == 1 and heads[hs[0]]["page"]]
    offset = _median(offs) if len(offs) >= 2 else None

    used, toc_to_head, last = set(), {}, -1
    for ti, e in enumerate(toc):
        avail = [hi for hi in cand[ti] if hi not in used]
        if not avail:
            continue
        tp = _arabic(e["page"])
        if offset is not None and tp is not None:
            target = tp + offset
            best = min(avail, key=lambda hi: (abs((heads[hi]["page"] or 0) - target), hi))
        else:                              # order-preserving fallback
            fwd = [hi for hi in avail if hi > last]
            best = (fwd or avail)[0]
        used.add(best)
        toc_to_head[ti] = best
        last = max(last, best)
    head_to_toc = {hi: ti for ti, hi in toc_to_head.items()}

    rows, flushed = [], set()

    def flush_missed_before(ti_limit):
        for ti, e in enumerate(toc):
            if ti < ti_limit and ti not in toc_to_head and ti not in flushed:
                flushed.add(ti)
                rows.append({"status": "missed", "toc": e, "heading": None})

    for hi, h in enumerate(heads):
        ti = head_to_toc.get(hi)
        if ti is not None:
            flush_missed_before(ti)
            e = toc[ti]
            row = {"status": "match", "toc": e, "heading": h}
            if e["level"] and h["level"]:
                row["expected"] = min(e["level"], 6)
                if h["level"] != row["expected"]:
                    row["status"] = "level?"
            rows.append(row)
        else:
            rows.append({"status": "extra", "toc": None, "heading": h})
    for ti, e in enumerate(toc):
        if ti not in toc_to_head and ti not in flushed:
            rows.append({"status": "missed", "toc": e, "heading": None})
    return rows


def compare(slug):
    od = output_dir(slug)
    if not (od / "ir.json").exists():
        raise FileNotFoundError(slug)
    toc = _parse_toc(_toc_blocks(od))
    heads = _headings(od)
    rows = _reconcile(toc, heads)
    summary = {
        "hasToc": bool(toc),
        "tocEntries": len(toc),
        "headings": len(heads),
        "matched": sum(1 for r in rows if r["status"] == "match"),
        "levelFlags": sum(1 for r in rows if r["status"] == "level?"),
        "missed": sum(1 for r in rows if r["status"] == "missed"),
        "extra": sum(1 for r in rows if r["status"] == "extra"),
    }
    return {"summary": summary, "rows": rows}
