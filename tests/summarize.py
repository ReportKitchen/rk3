"""Build the reviewable per-document summary used by both the snapshot test
and the curated expectations. Intentionally coarse: it should change when
document *structure* changes, not when an internal threshold wiggles without
visible effect."""

import json
from collections import Counter
from pathlib import Path

from rk3 import irwalk

ROOT = Path(__file__).resolve().parent.parent


def node_texts(nodes):
    """Every piece of user-visible text, at any depth — same walker as the
    engine (unified container model: leaves carry text, containers carry
    children), plus the fielded footnote records."""
    for n in irwalk.walk(nodes):
        if n.get("text"):
            yield n["text"]
        for note in n.get("notes", []):
            yield note["text"]


def summarize(slug: str) -> dict:
    outdir = ROOT / "output" / "pdfium" / slug
    meta = json.loads((outdir / "meta.json").read_text())
    if meta["status"] != "done":
        return {"status": meta["status"], "error": (meta.get("error") or "")[:120]}

    ir = json.loads((outdir / "ir.json").read_text())
    body = ir["body"]
    counts = Counter(n["type"] for n in body)
    notes = next((n["notes"] for n in body if n["type"] == "footnotes"), [])
    return {
        "status": "done",
        "title": ir.get("title", ""),
        "headings": [[n["level"], n["text"][:80]] for n in body
                     if n["type"] == "heading"],
        "counts": dict(sorted(counts.items())),
        "asideChildren": sum(len(n.get("children", [])) for n in body
                             if n["type"] == "aside"),
        "notes": [n["n"] for n in notes],
        "questions": len(ir.get("questions", [])),
        "textChars": sum(len(t) for t in node_texts(body)),
    }
