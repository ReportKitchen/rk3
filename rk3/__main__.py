"""CLI for direct pipeline runs:  python -m rk3 list | convert <slug> [--force]"""

import json
import sys

from .documents import list_documents
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
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
