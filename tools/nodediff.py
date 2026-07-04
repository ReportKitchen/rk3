"""Leaf-walk differ: a doc's committed IR vs its working-tree IR.

Walks both ir.json files as an ordered list of text leaves and prints a
unified diff of `p{page} {type}: {text[:110]}` lines. This is the
adjudication tool the webified §0.1 snapshot ritual calls for: it turns a
giant ir.json blob diff into the human-readable "what actually changed in
the reading stream" view, so an intended reflow reads differently from a
content regression.

    python tools/nodediff.py <slug>                 # HEAD vs working tree
    python tools/nodediff.py <slug> --ref <gitref>  # <gitref> vs working tree
"""

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rk3 import irwalk                       # noqa: E402
from rk3.documents import output_dir         # noqa: E402


def leaf_lines(ir):
    """One line per text leaf, in reading order: `p{page} {type}: {text}`."""
    out = []
    for n in irwalk.leaves(ir.get("body", [])):
        text = " ".join((n.get("text") or "").split())[:110]
        out.append(f"p{n.get('page')} {n.get('type')}: {text}")
    return out


def _current_ir(slug):
    p = output_dir(slug) / "ir.json"
    return json.loads(p.read_text()) if p.exists() else None


def _ref_ir(slug, ref):
    rel = f"output/pdfium/{slug}/ir.json"
    r = subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return json.loads(r.stdout)


def diff(slug, ref="HEAD"):
    cur = _current_ir(slug)
    if cur is None:
        return f"no working-tree ir.json for {slug!r} (convert it first)"
    old = _ref_ir(slug, ref)
    old_lines = leaf_lines(old) if old else []
    cur_lines = leaf_lines(cur)
    ud = difflib.unified_diff(old_lines, cur_lines,
                              fromfile=f"{ref}:{slug}",
                              tofile=f"working:{slug}", lineterm="")
    return "\n".join(ud)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug")
    ap.add_argument("--ref", default="HEAD",
                    help="git ref to compare against (default HEAD)")
    a = ap.parse_args()
    out = diff(a.slug, a.ref)
    print(out if out.strip() else f"(no leaf-stream changes for {a.slug} vs {a.ref})")


if __name__ == "__main__":
    main()
