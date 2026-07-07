"""Baseline scoreboard (webified §1.1).

For every converted doc, emit output/pdfium/<slug>/scoreboard.json — one
record per page:

    {page, class, visionIssues:{critical,high,medium,low},
     stakes:{green,red}, openOwnerNotes}

`class` is left as whatever a prior triage (§2) wrote (null until then).
Stakes come live from rk3.eval.checks_with_status (no reconvert); each check
is attributed to a page by its anchoring nid's page, else a `pNN` in its note,
else the doc-level bucket (page=null). Vision issues and owner notes come from
feedback/<slug>.jsonl: OPEN vision-qa records counted by severity; owner-typed
notes (type comment/answer, no `source`, status!=cleared) counted as open
owner notes.

    python tools/scoreboard.py            # all docs
    python tools/scoreboard.py <slug>     # one doc
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rk3 import irwalk, triage                            # noqa: E402
from rk3.documents import list_documents, output_dir     # noqa: E402
from rk3.eval import checks_with_status                   # noqa: E402

FEEDBACK = ROOT / "feedback"
_PAGE_RE = re.compile(r"\bp(\d{1,4})\b")


def _page_from_note(note):
    m = _PAGE_RE.search(note or "")
    return int(m.group(1)) if m else None


def _blank_page(p):
    return {"page": p, "class": None, "scanned": False,
            "visionIssues": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "stakes": {"green": 0, "red": 0}, "openOwnerNotes": 0}


def _scanned_pages(slug):
    """Pages a vision scan has actually touched — signalled by the render crop
    the scanner writes (qa/our-page-NNNN.png). Drives the gallery's HONESTY rule
    (webified §1.5a): a never-scanned page is grey, never a fake green."""
    d = output_dir(slug) / "qa"
    out = set()
    for f in sorted(d.glob("our-page-*.png")) if d.is_dir() else []:
        m = re.search(r"our-page-(\d+)\.png$", f.name)
        if m:
            out.add(int(m.group(1)))
    return out


def _feedback(slug):
    path = FEEDBACK / f"{slug}.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def _page_pngs(slug):
    d = output_dir(slug) / "pages"
    ps = []
    for f in sorted(d.glob("page-*.png")) if d.is_dir() else []:
        m = re.search(r"page-(\d+)\.png$", f.name)
        if m:
            ps.append(int(m.group(1)))
    return ps


def build(slug):
    """Compute and write scoreboard.json for one doc. Returns the board dict,
    or None if the doc has no IR yet."""
    ir_path = output_dir(slug) / "ir.json"
    if not ir_path.exists():
        return None
    ir = json.loads(ir_path.read_text())
    body = ir.get("body", [])
    nid_page = {n["nid"]: n.get("page") for n in irwalk.walk(body) if n.get("nid")}

    # pages: the rendered set, unioned with any page a node claims (so a page
    # with content but no png, or vice-versa, still shows up)
    pages = set(_page_pngs(slug)) | {p for p in nid_page.values() if p}
    pages = sorted(pages)

    sb_path = output_dir(slug) / "scoreboard.json"
    board = {p: _blank_page(p) for p in pages}
    doclevel = _blank_page(None)
    for p in _scanned_pages(slug):
        if p in board:
            board[p]["scanned"] = True
    # class from the deterministic triage (§2)
    try:
        for p, info in triage.triage_doc(slug).items():
            if p in board:
                board[p]["class"] = info["class"]
    except Exception:
        pass

    def rec_for(p):
        return board.get(p, doclevel)

    # stakes (live)
    for c in checks_with_status(slug):
        p = nid_page.get(c.get("nid")) or _page_from_note(c.get("note"))
        rec_for(p)["stakes"]["green" if c.get("ok") else "red"] += 1

    # feedback: vision issues + owner notes
    for e in _feedback(slug):
        if e.get("status") == "cleared":
            continue
        p = e.get("page")
        if p is None and e.get("nid"):
            p = nid_page.get(e["nid"])
        rec = rec_for(p)
        if e.get("source") == "vision-qa":
            if e.get("disposition", "open") == "open":
                sev = e.get("severity")
                if sev in rec["visionIssues"]:
                    rec["visionIssues"][sev] += 1
        elif e.get("type") in ("comment", "answer") and not e.get("source"):
            rec["openOwnerNotes"] += 1

    ordered = [board[p] for p in pages]
    if any(doclevel[k] != _blank_page(None)[k] for k in ("stakes", "visionIssues", "openOwnerNotes")):
        ordered.append(doclevel)
    out = {"slug": slug,
           "generated": datetime.datetime.now(datetime.timezone.utc)
                        .isoformat(timespec="seconds"),
           "pages": ordered}
    sb_path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def _summary_line(board):
    g = sum(p["stakes"]["green"] for p in board["pages"])
    r = sum(p["stakes"]["red"] for p in board["pages"])
    vi = sum(sum(p["visionIssues"].values()) for p in board["pages"])
    on = sum(p["openOwnerNotes"] for p in board["pages"])
    npages = sum(1 for p in board["pages"] if p["page"] is not None)
    return (f"{board['slug']:<52} pages={npages:<4} "
            f"stakes {g}g/{r}r  vision={vi}  ownerNotes={on}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", nargs="?", help="one doc; omit for all")
    a = ap.parse_args()
    slugs = ([a.slug] if a.slug
             else [d["slug"] for d in list_documents() if d.get("status") == "done"])
    n = 0
    for slug in slugs:
        board = build(slug)
        if board is None:
            print(f"{slug:<52} (no IR — skipped)")
            continue
        print(_summary_line(board))
        n += 1
    print(f"\nwrote {n} scoreboard.json file(s)")


if __name__ == "__main__":
    main()
