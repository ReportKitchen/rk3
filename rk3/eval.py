"""Conversion eval harness — data-driven spot-tests over the per-stage artifacts.

Each document has a spec at eval/<slug>.yaml listing checks. A check asserts an
OUTCOME against the converted artifacts:

  - order: [A, B]              A's text must read before B's  (catches column shuffles)
  - role:  {text, is, level?}  a node's type / heading level  (catches missed/spurious headings)

Checks anchor to content by text snippet — the same thing a future "create
assertion" right-click in the review UI would capture from a selection. On a
failure we localize to the earliest stage where the anchor breaks, so a
mis-ordering in the final IR isn't mistaken for an upstream extraction loss.

Runs through convert() so the per-stage fingerprint cache applies: the PDF is
opened once and only stages whose code VERSION / config / source changed re-run.

    python -m rk3 eval [slug]
"""

import json
import re

import yaml

from .documents import ROOT, output_dir
from .pipeline import ARTIFACTS, convert

EVAL_DIR = ROOT / "eval"


def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _walk(body):
    for n in body or []:
        yield n
        yield from _walk(n.get("children"))


def _artifact(slug, stage):
    p = output_dir(slug) / ARTIFACTS[stage]
    return json.loads(p.read_text()) if p.exists() else None


def _reading_order(ir):
    """Text-bearing nodes in document (reading) order."""
    return [n for n in _walk(ir.get("body", []))
            if n.get("type") in ("paragraph", "heading") and n.get("text")]


def _find(seq, snippet):
    s = _norm(snippet)
    for i, n in enumerate(seq):
        if s in _norm(n.get("text")):
            return i
    return -1


def _blocks_has(slug, snippet):
    b = _artifact(slug, "assemble")
    if not b:
        return False
    text = _norm(" ".join(ln.get("text", "")
                          for blk in b.get("blocks", []) for ln in blk.get("lines", [])))
    return _norm(snippet) in text


def _localize(slug, snippet):
    """Point at the defect's stage: present by `assemble` → it's an analyze bug;
    gone by then → the text was lost in extract/assemble."""
    if _blocks_has(slug, snippet):
        return "present in assemble → defect is in analyze (ordering/typing)"
    return "missing by assemble → defect is upstream (extract/assemble lost the text)"


# ---- check evaluators: (ok, detail) ----
def _check_order(slug, seq, c):
    a, b = c["order"]
    ia, ib = _find(seq, a), _find(seq, b)
    if ia < 0:
        return False, f"{a!r} not found in IR — {_localize(slug, a)}"
    if ib < 0:
        return False, f"{b!r} not found in IR — {_localize(slug, b)}"
    if ia < ib:
        return True, f"{a!r} (#{ia}) before {b!r} (#{ib})"
    return False, (f"{a!r} (#{ia}) reads AFTER {b!r} (#{ib}) — "
                   "text present, so wrong order is an analyze bug")


def _check_role(slug, seq, c):
    r = c["role"]
    i = _find(seq, r["text"])
    if i < 0:
        return False, f"{r['text']!r} not found in IR — {_localize(slug, r['text'])}"
    n = seq[i]
    is_h = n.get("type") == "heading"
    want = r.get("is", "heading")
    if want == "not-heading":
        return (not is_h), (f"is a {n.get('type')}" if not is_h
                            else "is a heading, expected non-heading")
    if not is_h:
        return False, f"is a {n.get('type')}, expected heading"
    if "level" in r and n.get("level") != r["level"]:
        return False, f"heading level {n.get('level')}, expected {r['level']}"
    return True, "heading" + (f" level {n.get('level')}" if "level" in r else "")


EVALUATORS = {"order": _check_order, "role": _check_role}


def _eval_doc(path):
    spec = yaml.safe_load(path.read_text())
    slug = spec["doc"]
    convert(slug)  # cached; re-runs only changed stages
    ir = _artifact(slug, "analyze")
    print(f"\n{slug}")
    if ir is None:
        print("  ! no ir.json (conversion failed?)")
        return 0, len(spec.get("checks", []))
    seq = _reading_order(ir)
    npass = nfail = 0
    for c in spec.get("checks", []):
        kind = next((k for k in EVALUATORS if k in c), None)
        if not kind:
            print(f"  ????  {c.get('note', '(no note)')}: unknown check kind")
            nfail += 1
            continue
        ok, detail = EVALUATORS[kind](slug, seq, c)
        print(f"  {'PASS' if ok else 'FAIL'}  {c.get('note', '')}")
        if not ok:
            print(f"          ↳ {detail}")
        npass += ok
        nfail += not ok
    return npass, nfail


def run(slug=None):
    files = [EVAL_DIR / f"{slug}.yaml"] if slug else sorted(EVAL_DIR.glob("*.yaml"))
    files = [f for f in files if f.exists()]
    if not files:
        print(f"no eval specs found in {EVAL_DIR}")
        return 2
    P = F = 0
    for f in files:
        p, q = _eval_doc(f)
        P, F = P + p, F + q
    print(f"\n{'=' * 50}\n{P} passed, {F} failed")
    return 1 if F else 0
