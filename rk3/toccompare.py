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

# trailing printed page number, with optional dot/space leaders ("Title .... 18")
_PAGE_TAIL = re.compile(r"[\s.·•…\-—]*\b(\d{1,4})\s*$")
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
    """One outline entry per TOC line: {title, level, page, norm}."""
    entries = []
    for b in blocks:
        for ln in b.get("lines", []):
            raw = ln["text"].strip()
            if not raw:
                continue
            page = None
            m = _PAGE_TAIL.search(raw)
            title = raw
            if m:
                page = int(m.group(1))
                title = raw[:m.start()].strip()
            n = _norm(title)
            if len(n) < 2 or n in ("contents", "table of contents"):
                continue  # bare page numbers, dot rows, the TOC's own title
            level = None
            sm = _SEC_NUM.match(title)
            if _CHAPTER.match(title):
                level = 1
            elif sm:
                level = sm.group(1).count(".") + 1
            entries.append({"title": title, "level": level, "page": page,
                            "norm": _norm(title)})
    return entries


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
    """Greedy title match (exact norm, then containment); add a relative-level
    note where matched depths disagree. Returns (rows, extra-headings)."""
    used = set()
    rows = []
    for e in toc:
        best = next((i for i, h in enumerate(heads)
                     if i not in used and h["norm"] == e["norm"]), None)
        if best is None:
            best = next((i for i, h in enumerate(heads)
                         if i not in used and e["norm"] and h["norm"]
                         and min(len(e["norm"]), len(h["norm"])) >= 6
                         and (e["norm"] in h["norm"] or h["norm"] in e["norm"])),
                        None)
        if best is None:
            rows.append({"status": "missed", "toc": e, "heading": None})
        else:
            used.add(best)
            rows.append({"status": "match", "toc": e, "heading": heads[best]})

    # level note: the TOC's nesting depth is the level we'd ADOPT (depth N -> hN).
    # Flag where our detected h-level differs from that — e.g. a 1.x subsection
    # the TOC puts one below its chapter, which we rendered as a deep h6.
    for r in rows:
        if r["status"] == "match" and r["toc"]["level"] and r["heading"]["level"]:
            exp = min(r["toc"]["level"], 6)
            r["expected"] = exp
            if r["heading"]["level"] != exp:
                r["status"] = "level?"

    extras = [h for i, h in enumerate(heads) if i not in used]
    return rows, extras


def compare(slug):
    od = output_dir(slug)
    if not (od / "ir.json").exists():
        raise FileNotFoundError(slug)
    toc = _parse_toc(_toc_blocks(od))
    heads = _headings(od)
    rows, extras = _reconcile(toc, heads)
    summary = {
        "hasToc": bool(toc),
        "tocEntries": len(toc),
        "headings": len(heads),
        "matched": sum(1 for r in rows if r["status"] == "match"),
        "levelFlags": sum(1 for r in rows if r["status"] == "level?"),
        "missed": sum(1 for r in rows if r["status"] == "missed"),
        "extra": len(extras),
    }
    return {"summary": summary, "rows": rows, "extras": extras}
