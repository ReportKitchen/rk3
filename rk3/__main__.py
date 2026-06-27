"""CLI for direct pipeline runs:
  python -m rk3 list                         list documents and conversion status
  python -m rk3 convert <slug> [--force]     convert a document (--force reconverts)
  python -m rk3 remove <slug|file.pdf>       delete a document and all its artifacts
  python -m rk3 eval [slug]                  run conversion spot-test assertions
"""

import json
import sys

from .documents import list_documents, remove_document, resolve_slug
from .pipeline import convert


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
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
