"""Regenerate tests/snapshot.json from the current corpus output.

Run after an intentional rule change, then REVIEW THE GIT DIFF: every changed
line is a document whose structure your change touched.

    .venv/bin/python -m tests.regen
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rk3.documents import list_documents  # noqa: E402
from rk3.pipeline import convert  # noqa: E402
from tests.summarize import summarize  # noqa: E402


def main():
    snapshot = {}
    for d in list_documents():
        convert(d["slug"])
        snapshot[d["slug"]] = summarize(d["slug"])
    out = Path(__file__).parent / "snapshot.json"
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out} ({len(snapshot)} documents)")


if __name__ == "__main__":
    main()
