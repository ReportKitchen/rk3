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

from rk3.documents import output_dir

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


def _parse_toc(blocks):
    """One outline entry per TOC line: {title, level, page, x, norm}. Lines that
    start lowercase are wraps of the previous entry (TOC titles otherwise start
    capitalized) and get folded back in. Levels are assigned afterwards."""
    entries = []
    for b in blocks:
        for ln in b.get("lines", []):
            raw = ln["text"].strip()
            if not raw:
                continue
            x = ln["bbox"][0]
            page = None
            m = _PAGE_TAIL.search(raw)
            body = raw
            if m:
                page = m.group(1) or m.group(2)   # arabic or roman (string)
                body = raw[:m.start()].strip()
            body = re.sub(r"[\s.·•…_]{2,}$", "", body).strip()  # trailing dot leaders
            first = next((c for c in body if c.isalpha()), "")
            if entries and first and first.islower():
                e = entries[-1]                      # line wrap: fold into previous
                e["title"] = f"{e['title']} {body}".strip()
                if e["page"] is None:
                    e["page"] = page
                e["norm"] = _norm(e["title"])
                continue
            n = _norm(body)
            if len(n) < 2 or n in ("contents", "table of contents"):
                continue  # bare page numbers, dot rows, the TOC's own title
            entries.append({"title": body, "level": None, "page": page,
                            "x": x, "norm": n})
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


def _reconcile(toc, heads):
    """Match TOC entries to headings (greedy by normalized title), then emit one
    unified list in OUR document order: every detected heading is a row (with its
    TOC counterpart, or blank when it's below TOC depth), and TOC entries with no
    heading are interleaved as 'missed' rows in TOC order."""
    match_for_head = {}     # heading index -> toc index
    toc_to_head = {}        # toc index -> heading index
    used = set()
    for ti, e in enumerate(toc):
        best = next((i for i, h in enumerate(heads)
                     if i not in used and h["norm"] == e["norm"]), None)
        if best is None:
            best = next((i for i, h in enumerate(heads)
                         if i not in used and e["norm"] and h["norm"]
                         and min(len(e["norm"]), len(h["norm"])) >= 6
                         and (e["norm"] in h["norm"] or h["norm"] in e["norm"])),
                        None)
        if best is not None:
            used.add(best)
            match_for_head[best] = ti
            toc_to_head[ti] = best

    def row_for_match(hi, ti):
        e, h = toc[ti], heads[hi]
        row = {"status": "match", "toc": e, "heading": h}
        # TOC nesting depth is the level we'd ADOPT (depth N -> hN); flag drift
        if e["level"] and h["level"]:
            row["expected"] = min(e["level"], 6)
            if h["level"] != row["expected"]:
                row["status"] = "level?"
        return row

    rows = []
    flushed = set()

    def flush_missed_before(ti_limit):
        for ti, e in enumerate(toc):
            if ti < ti_limit and ti not in toc_to_head and ti not in flushed:
                flushed.add(ti)
                rows.append({"status": "missed", "toc": e, "heading": None})

    for hi, h in enumerate(heads):
        ti = match_for_head.get(hi)
        if ti is not None:
            flush_missed_before(ti)      # TOC entries we skipped past, unmatched
            rows.append(row_for_match(hi, ti))
        else:
            rows.append({"status": "extra", "toc": None, "heading": h})
    for ti, e in enumerate(toc):         # any remaining unmatched TOC entries
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
