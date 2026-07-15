"""Place freshly-synced source PDFs into their numbered folders.

The S3 bucket stores PDFs flat under sources/, but the pipeline discovers
documents with sources/<folder>/<name>.pdf (list_documents globs '*/*.pdf')
and identifies each by the slug <folder>--<name>. A PDF must therefore sit
in the same folder as its committed sidecars (<stem>.config.json etc.), which
are what encode the human's folder assignment.

This moves each top-level sources/*.pdf into the folder that already holds a
sidecar for that exact stem. PDFs with no matching sidecar are left in place
and reported (they have no config/eval yet, so the pipeline ignores them).

Usage:
  python -m tools.place_sources            # report only (dry run)
  python -m tools.place_sources --apply    # perform the moves
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"

# sidecar suffixes that mark a PDF stem as "belonging" to a folder
_SIDECARS = (".config.json", ".ops.json", ".landing.json",
             ".landing-theme.json", ".landing-ai.json")
# folders that never hold processed source PDFs
_SKIP_FOLDERS = {"docs", "inactive"}


def _stem_to_folder() -> dict[str, str]:
    """Map a PDF stem -> folder name, from existing sidecar files."""
    mapping: dict[str, str] = {}
    for folder in SOURCES.iterdir():
        if not folder.is_dir() or folder.name in _SKIP_FOLDERS:
            continue
        for sidecar in folder.iterdir():
            for suf in _SIDECARS:
                if sidecar.name.endswith(suf):
                    stem = sidecar.name[: -len(suf)]
                    mapping.setdefault(stem, folder.name)
    return mapping


def place(apply: bool) -> int:
    if not SOURCES.is_dir():
        print("no sources/ directory; nothing to place")
        return 0
    mapping = _stem_to_folder()
    flat = sorted(p for p in SOURCES.glob("*.pdf"))
    moved, deduped, unmatched = 0, 0, []
    for pdf in flat:
        folder = mapping.get(pdf.stem)
        if not folder:
            unmatched.append(pdf.name)
            continue
        dest = SOURCES / folder / pdf.name
        if dest.exists():
            # canonical copy already in the folder; the flat one is a re-sync
            # duplicate (additive `aws s3 sync` refills the top level). Drop it
            # so duplicates don't accumulate across sessions.
            if apply:
                pdf.unlink()
            print(f"{'deduped' if apply else 'would dedupe'}: {pdf.name} "
                  f"(already in {folder}/)")
            deduped += 1
            continue
        if apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            pdf.rename(dest)
        print(f"{'moved' if apply else 'would move'}: {pdf.name} -> {folder}/")
        moved += 1
    if unmatched:
        print(f"\n{len(unmatched)} unmatched (no sidecar, left in place):")
        for name in unmatched:
            print(f"  {name}")
    verb = "moved" if apply else "to move"
    print(f"\n{moved} PDF(s) {verb}; {deduped} deduped; "
          f"{len(unmatched)} unmatched.")
    return 0


if __name__ == "__main__":
    sys.exit(place("--apply" in sys.argv[1:]))
