"""Guidance engine — reads a converted document and advises what content earns a
place on a landing page. The editorial spine of the Assemble experience: it
produces the smart default page (which blocks, in what order, at what length) and
the per-block guidance the UI shows.

Two tiers:
  1. PROFILE — deterministic, from the IR (pages, words, sections, whole-doc text)
  2. JUDGMENT — one grounded AI call that extracts substantive stats + real
     stories (people AND case studies) and returns per-block verdicts + reasons +
     a recommended default page.

Prompts live in the content registry (shared.analysis.*), so the voice/definitions
are editable without touching code. The JSON schema is the code contract and stays
here. AI-only: there is no heuristic guidance (see conversion philosophy — the AI
does the reading so the user doesn't have to). Callers cache the result per doc.
"""
import re

from rk3 import content
from rk3.ai import complete_json


def _walk(nodes):
    for n in nodes or []:
        yield n
        yield from _walk(n.get("children"))


# ---- tier 1: deterministic profile (incl. the whole-doc text the model reads) ----
def _full_text(ir: dict, cap: int = 240000) -> str:
    """Every text node in reading order — headings marked, list items bulleted,
    and a [p. N] marker whenever the page changes so the model can cite real page
    numbers for stats/stories. (A front-only window is why the old extractor
    grabbed funders over outcomes.)"""
    out, total, last_page = [], 0, None
    for n in _walk(ir.get("body", [])):
        pg = n.get("page")
        if pg and pg != last_page:
            out.append(f"\n[p. {pg}]")
            last_page = pg
        t, txt = n.get("type"), (n.get("text") or "").strip()
        if not txt:
            continue
        line = f"\n## {txt}" if t == "heading" else (f"- {txt}" if t == "item" else txt)
        out.append(line)
        total += len(line)
        if total > cap:
            break
    return "\n".join(out)


def profile(ir: dict) -> dict:
    body = ir.get("body", [])
    heads = [n for n in _walk(body) if n.get("type") == "heading" and n.get("text", "").strip()]
    words = sum(len(n["text"].split()) for n in _walk(body) if n.get("text", "").strip())
    seq = list(_walk(body))
    intro = next((h for h in heads if re.search(
        r"executive summary|abstract|overview|introduction", h.get("text", ""), re.I)), None)
    intro_words = None
    if intro:
        i, lvl, intro_words = seq.index(intro), intro.get("level", 1), 0
        for n in seq[i + 1:]:
            if n.get("type") == "heading" and n.get("level", 9) <= lvl:
                break
            if n.get("text"):
                intro_words += len(n["text"].split())
    pages = (len(ir.get("pages") or {})
             or max((n.get("page") or 0 for n in seq), default=0)
             or max(1, round(words / 450)))  # exact from IR; estimate only as last resort
    return {
        "title": ir.get("title", ""),
        "approxWords": words,
        "pages": pages,
        "headings": len(heads),
        "introSectionWords": intro_words,
    }


# ---- tier 2: the JSON schema (code contract; Anthropic needs additionalProperties:false) ----
_BLOCK_KEYS = ["aiSummary", "execSummary", "highlights", "findings", "toc",
               "storytelling", "download", "secondary", "share"]
_VERDICT = {"type": "object", "additionalProperties": False,
            "required": ["verdict", "note"],
            "properties": {"verdict": {"type": "string", "enum": ["recommended", "optional", "skip"]},
                           "note": {"type": "string"}}}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["documentRead", "stats", "stories", "recommendedPage", "reasons", "blocks"],
    "properties": {
        "documentRead": {"type": "object", "additionalProperties": False,
                         "required": ["whatItIs", "audience", "coreMessage"],
                         "properties": {k: {"type": "string"} for k in ("whatItIs", "audience", "coreMessage")}},
        "stats": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                  "required": ["value", "fact", "page"],
                  "properties": {"value": {"type": "string"}, "fact": {"type": "string"},
                                 "page": {"type": "string"}}}},
        "stories": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                    "required": ["subject", "kind", "quote", "narrative", "attribution", "page", "strength"],
                    "properties": {"subject": {"type": "string"},
                                   "kind": {"type": "string", "enum": ["personal", "caseStudy"]},
                                   "quote": {"type": "string"},
                                   "narrative": {"type": "string"},
                                   "attribution": {"type": "string"},
                                   "page": {"type": "string"},
                                   "strength": {"type": "string", "enum": ["strongest", "solid", "thin"]}}}},
        "recommendedPage": {"type": "object", "additionalProperties": False,
                            "required": ["length", "coverLayout", "summaryChoice", "blocks"],
                            "properties": {"length": {"type": "string", "enum": ["short", "middle", "long"]},
                                           "coverLayout": {"type": "string", "enum": ["onTop", "beside", "inset", "textForward"]},
                                           "summaryChoice": {"type": "string", "enum": ["exec", "ai"]},
                                           "blocks": {"type": "array", "items": {"type": "string", "enum": _BLOCK_KEYS}}}},
        "reasons": {"type": "object", "additionalProperties": False,
                    "required": ["length", "summaryChoice", "coverLayout"],
                    "properties": {k: {"type": "string"} for k in ("length", "summaryChoice", "coverLayout")}},
        "blocks": {"type": "object", "additionalProperties": False,
                   "required": _BLOCK_KEYS, "properties": {k: _VERDICT for k in _BLOCK_KEYS}},
    },
}


def generate(ir: dict) -> dict:
    """Run the full guidance pass. Returns {profile, guidance}. Raises on any AI
    error — the caller decides whether to cache or retry (guidance is AI-only, so
    there's no heuristic fallback)."""
    p = profile(ir)
    system, model = content.prompt("shared.analysis.guidance_system")
    catalog, _ = content.prompt("shared.analysis.block_catalog")
    task, _ = content.prompt("shared.analysis.guidance_task")
    user = (
        f"Document title: {p['title']}\n"
        f"Length: {p['pages']} pages, ~{p['approxWords']} words. "
        f"Its intro/summary section runs ~{p['introSectionWords']} words.\n\n"
        f"{catalog}\n\nFULL DOCUMENT:\n{_full_text(ir)}\n\n{task}"
    )
    g = complete_json(system, user, SCHEMA, max_tokens=5000, model=model)
    return {"profile": p, "guidance": g}
