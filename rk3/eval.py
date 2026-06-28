"""Conversion eval harness — data-driven spot-tests over the per-stage artifacts.

Each document has a spec at eval/<slug>.yaml listing checks. A check asserts an
OUTCOME against the converted artifacts:

  - order: [A, B]              A's text must read before B's  (catches column shuffles)
  - role:  {text, is, level?}  a node's type / heading level  (catches missed/spurious headings)
  - list:  [I1, I2, ...]       these snippets are items of ONE list, in order
                               (catches un-reconstructed bullets and split lists)
  - merge: [A, B]              A and B belong to ONE node (catches over-split paragraphs)

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


STAGES = ("extract", "assemble", "analyze", "render")


def _stage_seq(slug, stage):
    """A stage's content as an ordered list of {text, type, level} — so a check
    can assert against the layer where the property actually lives.

      analyze  → IR text nodes (paragraphs/headings) with type + level
      assemble → blocks in stored order (text = joined lines; no type/level yet)
      extract  → one entry per page (concatenated chars)
    """
    if stage == "analyze":
        ir = _artifact(slug, "analyze") or {}
        return [{"text": n.get("text", ""), "type": n.get("type"), "level": n.get("level")}
                for n in _walk(ir.get("body", []))
                if n.get("type") in ("paragraph", "heading") and n.get("text")]
    if stage == "assemble":
        b = _artifact(slug, "assemble") or {}
        return [{"text": " ".join(ln.get("text", "") for ln in blk.get("lines", [])),
                 "type": None, "level": None, "page": blk.get("page")}
                for blk in b.get("blocks", [])]
    if stage == "extract":
        e = _artifact(slug, "extract") or {}
        return [{"text": "".join(c[0] for c in p.get("chars", [])),
                 "type": None, "level": None, "page": p.get("n")}
                for p in e.get("pages", [])]
    return []


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


# ---- check evaluators: (ok, detail). Each reads the check's target stage. ----
def _check_order(slug, c):
    stage = c.get("stage", "analyze")
    seq = _stage_seq(slug, stage)
    a, b = c["order"]
    ia, ib = _find(seq, a), _find(seq, b)
    if ia < 0:
        return False, f"{a!r} not found in {stage} — {_localize(slug, a)}"
    if ib < 0:
        return False, f"{b!r} not found in {stage} — {_localize(slug, b)}"
    if ia < ib:
        return True, f"{a!r} (#{ia}) before {b!r} (#{ib})"
    return False, f"{a!r} (#{ia}) reads AFTER {b!r} (#{ib}) — {_localize(slug, a)}"


def _check_role(slug, c):
    stage = c.get("stage", "analyze")
    if stage != "analyze":
        return False, f"role checks need the analyze stage (got {stage!r})"
    seq = _stage_seq(slug, "analyze")
    r = c["role"]
    i = _find(seq, r["text"])
    if i < 0:
        return False, f"{r['text']!r} not found in analyze — {_localize(slug, r['text'])}"
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


def _list_nodes(slug):
    ir = _artifact(slug, "analyze") or {}
    return [n for n in _walk(ir.get("body", [])) if n.get("type") == "list"]


def _check_list(slug, c):
    """All snippets must be items of a SINGLE list node, in order — pins missing
    list reconstruction (snippet lives in no list) and over-split lists (snippets
    scatter across separate lists, e.g. a UL broken over a page break)."""
    snippets = c["list"]
    lists = _list_nodes(slug)
    s0 = _norm(snippets[0])
    host = next((ln for ln in lists
                 if any(s0 in _norm(it) for it in ln.get("items", []))), None)
    if host is None:
        return False, f"first item {snippets[0]!r} is in no list — {_localize(slug, snippets[0])}"
    items = [_norm(it) for it in host.get("items", [])]
    last = -1
    for sn in snippets:
        ns = _norm(sn)
        pos = next((i for i in range(last + 1, len(items)) if ns in items[i]), -1)
        if pos < 0:
            split = any(ns in _norm(it) for o in lists
                        if o is not host for it in o.get("items", []))
            why = ("is in a different list (list split)" if split
                   else f"is not a list item — {_localize(slug, sn)}")
            return False, f"item {sn!r} {why}"
        last = pos
    return True, f"{len(snippets)} items in one list (#{lists.index(host)})"


def _check_merge(slug, c):
    """A and B should live in ONE text node — pins over-split paragraphs."""
    a, b = c["merge"]
    seq = _stage_seq(slug, "analyze")
    ia, ib = _find(seq, a), _find(seq, b)
    if ia < 0:
        return False, f"{a!r} not found — {_localize(slug, a)}"
    if ib < 0:
        return False, f"{b!r} not found — {_localize(slug, b)}"
    if ia == ib:
        return True, f"both in node #{ia}"
    return False, f"{a!r} (#{ia}) and {b!r} (#{ib}) are separate — should be one paragraph"


EVALUATORS = {"order": _check_order, "role": _check_role,
              "list": _check_list, "merge": _check_merge}


def _eval_doc(path):
    spec = yaml.safe_load(path.read_text())
    slug = spec["doc"]
    convert(slug)  # cached; re-runs only changed stages
    print(f"\n{slug}")
    if _artifact(slug, "analyze") is None:
        print("  ! no ir.json (conversion failed?)")
        return 0, len(spec.get("checks", []))
    npass = nfail = 0
    for c in spec.get("checks", []):
        kind = next((k for k in EVALUATORS if k in c), None)
        stage = c.get("stage", "analyze")
        if not kind:
            print(f"  ????  {c.get('note', '(no note)')}: unknown check kind")
            nfail += 1
            continue
        ok, detail = EVALUATORS[kind](slug, c)
        print(f"  {'PASS' if ok else 'FAIL'}  [{stage:>8}]  {c.get('note', '')}")
        if not ok:
            print(f"             ↳ {detail}")
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
