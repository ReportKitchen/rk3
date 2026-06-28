"""CLI for direct pipeline runs:
  python -m rk3 list                         list documents and conversion status
  python -m rk3 convert <slug> [--force]     convert a document (--force reconverts)
  python -m rk3 remove <slug|file.pdf>       delete a document and all its artifacts
  python -m rk3 eval [slug]                  run conversion spot-test assertions
  python -m rk3 feedback [category]          list review notes (optionally by category:
                                             structure | styling | figure | pattern)
"""

import json
import sys

from .documents import ROOT, list_documents, remove_document, resolve_slug
from .pipeline import convert


def show_feedback(category=None):
    """Active review notes across all docs, optionally filtered by category."""
    fb_dir = ROOT / "feedback"
    n = 0
    for path in sorted(fb_dir.glob("*.jsonl")) if fb_dir.is_dir() else []:
        rows = []
        for line in path.read_text().splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("type") != "comment" or e.get("status") == "cleared":
                continue
            if category and e.get("category") != category:
                continue
            rows.append(e)
        if not rows:
            continue
        print(f"\n{path.stem}")
        for e in rows:
            cat = e.get("category") or "—"
            where = f"p{e.get('page')}" + (f" {e['nid']}" if e.get("nid") else "")
            print(f"  [{cat:9}] {where:18} {e.get('text', '').strip()}")
            n += 1
    print(f"\n{n} note(s)" + (f" in category {category!r}" if category else ""))


def main():
    args = sys.argv[1:]
    if args[:1] == ["list"]:
        for d in list_documents():
            print(f"{d['status']:>12}  {d['slug']}")
    elif args[:1] == ["convert"] and len(args) >= 2:
        meta = convert(args[1], force="--force" in args)
        print(json.dumps(meta, indent=2))
        sys.exit(0 if meta["status"] == "done" else 1)
    elif args[:1] == ["remove"] and len(args) >= 2:
        slug = resolve_slug(args[1])
        removed = remove_document(slug)
        if not removed:
            print(f"Nothing to remove for {args[1]!r}")
            sys.exit(1)
        print(f"Removed {slug}:")
        for p in removed:
            print(f"  {p}")
    elif args[:1] == ["eval"]:
        from .eval import run
        sys.exit(run(args[1] if len(args) >= 2 else None))
    elif args[:1] == ["feedback"]:
        show_feedback(args[1] if len(args) >= 2 else None)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
