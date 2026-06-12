"""Corpus regression tests.

Two layers:
- curated expectations (expectations.json): human-meaningful invariants,
  mostly distilled from resolved viewer feedback. These are the rules we've
  explicitly committed to; a failure here is a regression, full stop.
- snapshot (snapshot.json): auto-generated structural summary of every
  document. A failure here means a rule change had visible blast radius —
  regenerate with `python -m tests.regen` and REVIEW THE GIT DIFF doc by doc
  before committing it.
"""

import json
from pathlib import Path

import pytest

from .summarize import node_texts, summarize

HERE = Path(__file__).parent
ROOT = HERE.parent

EXPECTATIONS = json.loads((HERE / "expectations.json").read_text())
SNAPSHOT = json.loads((HERE / "snapshot.json").read_text()) \
    if (HERE / "snapshot.json").exists() else {}


def _ir(slug):
    return json.loads((ROOT / "output" / "pdfium" / slug / "ir.json").read_text())


@pytest.mark.parametrize("slug", sorted(EXPECTATIONS))
def test_expectations(corpus, slug):
    exp = EXPECTATIONS[slug]
    meta = corpus[slug]

    if "status" in exp:
        assert meta["status"] == exp["status"]
        if "error_contains" in exp:
            assert exp["error_contains"] in (meta.get("error") or "")
        if exp["status"] != "done":
            return

    ir = _ir(slug)
    body = ir["body"]
    full_text = "\n".join(node_texts(body))
    headings = [[n["level"], n["text"]] for n in body if n["type"] == "heading"]

    for needle in exp.get("text_contains", []):
        assert needle in full_text, f"missing text: {needle!r}"
    for needle in exp.get("text_not_contains", []):
        assert needle not in full_text, f"forbidden text present: {needle!r}"
    for lv, text in exp.get("headings_include", []):
        assert any(h[0] == lv and h[1].startswith(text) for h in headings), \
            f"missing h{lv} starting {text!r}; have {headings}"
    for lv, text in exp.get("headings_exclude", []):
        assert not any(h[0] == lv and h[1].startswith(text) for h in headings), \
            f"unwanted h{lv} {text!r} present"
    for ntype, count in exp.get("counts", {}).items():
        actual = sum(1 for n in body if n["type"] == ntype)
        assert actual == count, f"{ntype}: expected {count}, got {actual}"
    if "notes_sequential" in exp:
        notes = next((n["notes"] for n in body if n["type"] == "footnotes"), [])
        nums = [n["n"] for n in notes]
        lo, hi = exp["notes_sequential"]
        assert nums == list(range(lo, hi + 1)), \
            f"notes not sequential {lo}..{hi}: {nums[:10]}…"
    if "aside_first_child_starts" in exp:
        for page, prefix in exp["aside_first_child_starts"]:
            aside = next(n for n in body
                         if n["type"] == "aside" and n["page"] == page)
            first = aside["children"][0].get("text", "")
            assert first.startswith(prefix), \
                f"p{page} aside first child {first[:60]!r}"


@pytest.mark.parametrize("slug", sorted(SNAPSHOT))
def test_snapshot(corpus, slug):
    assert slug in corpus, f"document {slug} missing from sources"
    actual = summarize(slug)
    expected = SNAPSHOT[slug]
    assert actual == expected, (
        f"structural change in {slug}.\n"
        f"If intended: python -m tests.regen, then review the git diff of "
        f"tests/snapshot.json before committing."
    )
