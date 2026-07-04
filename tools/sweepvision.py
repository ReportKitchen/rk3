"""Sweep stale vision-QA issues (webified §1.2, reused in §7).

For a doc with OPEN `source: vision-qa` feedback records, re-scan the pages
those records reference (one batched browser session) and mark any open issue
the fresh scan no longer reproduces (same page + same category + similar text)
as `disposition: "fixed"` with an auto-swept note. Owner-typed notes (no
`source`) are never touched. The review board shrinks to reality.

    python tools/sweepvision.py <slug> [--model claude-haiku-4-5] [--dry-run]
    python tools/sweepvision.py --all   # every doc that has open vision records

Nondeterminism note: the reviewer is a vision model, so a false "fixed" is
possible (a real issue simply not re-flagged this pass). That is acceptable by
design — these are auto-flags, not owner notes; a later scan re-adds a genuine
issue. Matching is deliberately lenient (keep-open-biased) to minimise it.
"""

import argparse
import datetime
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rk3.ai import usage_summary                 # noqa: E402
from rk3.documents import list_documents         # noqa: E402
from rk3.visionqa import qa_doc                   # noqa: E402

FEEDBACK = ROOT / "feedback"
_MATCH = 0.45   # normalized-text similarity at/above which an issue is "still reported"


def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _open_vision(recs):
    return [r for r in recs
            if r.get("source") == "vision-qa"
            and r.get("disposition", "open") == "open"
            and r.get("status") != "cleared"]


def _reproduced(rec, fresh):
    """Does any fresh flag match this record (same page, same category, similar
    text)? Lenient on purpose — bias toward keeping issues open."""
    rp, rc, rt = rec.get("page"), rec.get("category"), _norm(rec.get("text"))
    best = 0.0
    for f in fresh:
        if f.get("page") != rp or f.get("category") != rc:
            continue
        best = max(best, difflib.SequenceMatcher(None, rt, _norm(f.get("issue"))).ratio())
    return best >= _MATCH, best


def sweep(slug, model=None, dry_run=False):
    path = FEEDBACK / f"{slug}.jsonl"
    if not path.exists():
        return {"slug": slug, "open": 0, "swept": 0}
    recs = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    openv = _open_vision(recs)
    if not openv:
        return {"slug": slug, "open": 0, "swept": 0}
    pages = sorted({r.get("page") for r in openv if r.get("page") is not None})
    fresh = qa_doc(slug, pages=pages, model=model)   # one browser session
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    swept = 0
    for rec in recs:
        if rec not in openv:
            continue
        ok, _ = _reproduced(rec, fresh)
        if not ok:
            swept += 1
            if not dry_run:
                rec["disposition"] = "fixed"
                rec["dispositionAt"] = now
                rec["dispositionNote"] = f"auto-swept: not reproduced by rescan {now[:10]}"
    if not dry_run and swept:
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
    return {"slug": slug, "open": len(openv), "pages": pages,
            "freshFlags": len(fresh), "swept": swept}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--model", default=None, help="reviewer model override")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.all:
        slugs = []
        for d in list_documents():
            p = FEEDBACK / f"{d['slug']}.jsonl"
            if p.exists() and _open_vision(
                    [json.loads(l) for l in p.read_text().splitlines() if l.strip()]):
                slugs.append(d["slug"])
    elif a.slug:
        slugs = [a.slug]
    else:
        ap.error("give a slug or --all")

    before = usage_summary()["cost"]
    for slug in slugs:
        r = sweep(slug, model=a.model, dry_run=a.dry_run)
        print(f"{slug}: open={r['open']} freshFlags={r.get('freshFlags','-')} "
              f"swept={r['swept']}{' (dry-run)' if a.dry_run else ''}")
    spent = round(usage_summary()["cost"] - before, 3)
    print(f"\nvision spend this sweep: ${spent}")


if __name__ == "__main__":
    main()
