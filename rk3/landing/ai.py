"""AI content pass for the Landing Page Maker.

Given a document's IR, generate higher-quality starter content than the
deterministic heuristics can: a multi-piece title, executive-summary variants,
and genuine key findings. Grounded in the document text; the model is told not
to invent facts. Falls back to heuristics on any error (see callers).

Summaries vary on two axes — voice (STYLES) and length (LENGTHS). The upfront
pass generates the three styles at the default length in one call; other
(style, length) combinations are generated lazily, on demand, and cached.
"""

import re

from rk3.ai import complete_json
from rk3.landing.extract import _flat, _walk
from rk3.prompts import load_prompt

# summary voice, composed into both the upfront and the lazy prompts
STYLES = {
    "intro": (
        "a report-introduction style. Open with one or two punchy sentences about "
        "how the subject shows up in the real world (a hook), then introduce what "
        "the document sets out to do. This MAY use first person ('we') and refer to "
        "'this report'."),
    "neutral": (
        "a plain executive summary in neutral, subject-focused third person: the "
        "topic, findings, and why they matter. Do NOT name or refer to the "
        "publishing organization, do NOT say 'this report'/'the report', and do NOT "
        "use first person — lead with the subject matter itself."),
    "hardsell": (
        "a high-impact, persuasive summary that stresses the importance, urgency, "
        "and real-world stakes of the work. Make it compelling, but do not "
        "exaggerate beyond, or invent anything not supported by, the document."),
}
LENGTHS = {
    "short": "Keep it to 2–3 sentences.",
    "medium": "Write a single full paragraph (roughly 5–8 sentences).",
    "long": "Write 3–4 short paragraphs.",
}
DEFAULT_STYLE = "intro"
DEFAULT_LENGTH = "medium"

# landing-page LLM system prompts live under prompts/ (see prompts/README.md)
SYSTEM = load_prompt("landing-copy.system.md")

# upfront pass: title + the three summary styles (at the default length) + findings
SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "object",
            "properties": {
                "eyebrow": {"type": "string"},
                "title": {"type": "string"},
                "subtitle": {"type": "string"},
            },
            "required": ["eyebrow", "title", "subtitle"],
            "additionalProperties": False,
        },
        "summaries": {
            "type": "object",
            "properties": {k: {"type": "string"} for k in STYLES},
            "required": list(STYLES),
            "additionalProperties": False,
        },
        "highlights": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "summaries", "highlights"],
    "additionalProperties": False,
}

_VARIANT_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
    "additionalProperties": False,
}


def _doc_text(ir: dict, limit: int = 7000) -> str:
    """A compact text view of the document for the model: headings + paragraphs
    in reading order, capped to keep token cost low."""
    parts = []
    for n in _walk(ir.get("body", [])):
        t = n.get("type")
        if t == "heading":
            parts.append(f"\n## {n.get('text', '').strip()}")
        elif t == "paragraph" and n.get("text"):
            parts.append(n["text"].strip())
        if sum(len(p) for p in parts) > limit:
            break
    return "\n".join(parts)[:limit]


def generate_landing_ai(ir: dict) -> dict:
    """Upfront pass. Returns {title, summaries, highlights} where summaries is
    keyed by ``"<style>:<length>"`` (the three styles at the default length), so
    it merges cleanly with lazily-generated variants."""
    title = (ir.get("title") or "").strip()
    styles_desc = "\n".join(f"   • {k} — {v}" for k, v in STYLES.items())
    user = (
        f"Document title: {title}\n\n"
        f"Document content:\n{_doc_text(ir)}\n\n"
        "Produce, as JSON:\n"
        "1. title — split the report title into: eyebrow (a short kicker/category "
        "or series name; may be empty), title (the main title), subtitle (the deck "
        "or descriptive sub-line; may be empty). Use the real title pieces; don't pad.\n"
        "2. summaries — THREE distinct executive-summary variants of the SAME "
        f"document, all accurate to it. {LENGTHS[DEFAULT_LENGTH]} Each in a distinct "
        f"voice:\n{styles_desc}\n"
        "3. highlights — 3–5 key findings as short, concrete bullet strings a reader "
        "would care about (outcomes, numbers, conclusions), each grounded in the document."
    )
    data = complete_json(SYSTEM, user, SCHEMA)
    sums = data.pop("summaries", {}) or {}
    data["summaries"] = {f"{k}:{DEFAULT_LENGTH}": v for k, v in sums.items() if v}
    return data


# ---- analyze tier: locate content, write nothing ----
ANALYZE_SYSTEM = load_prompt("landing-analyze.system.md")
_INTRO_SCHEMA = {
    "type": "object",
    "properties": {"heading_index": {"type": "integer"}},
    "required": ["heading_index"],
    "additionalProperties": False,
}


def find_intro_section(ir: dict):
    """Analyze-tier: pick the heading that begins the document's intro / executive
    summary / about section, so its verbatim text can be used as the Document
    Summary. Returns the exact heading text (to slice deterministically) or None.
    Generates no prose — it only points at an existing heading."""
    heads = [n for n in _flat(ir.get("body", []))
             if n.get("type") == "heading" and n.get("text", "").strip()]
    if not heads:
        return None
    listing = "\n".join(
        f"{j}. (level {n.get('level', '?')}) {n['text'].strip()[:90]}"
        for j, n in enumerate(heads))
    user = (
        "Here are the document's section headings, numbered:\n\n"
        f"{listing}\n\n"
        "Which heading begins the section that best works as the document's "
        "introduction or executive summary — a self-contained section a reader "
        "could read to understand what the document is about and what it "
        "concludes? Prefer an explicit summary / abstract / overview / "
        "introduction / 'about this …' section near the front. If none of the "
        "headings begins such a section, return -1.\n"
        'Return JSON: {"heading_index": <number, or -1>}.'
    )
    res = complete_json(ANALYZE_SYSTEM, user, _INTRO_SCHEMA)
    j = res.get("heading_index", -1)
    if isinstance(j, int) and 0 <= j < len(heads):
        return heads[j]["text"].strip()
    return None


FINDINGS_SYSTEM = load_prompt("landing-findings.system.md")
_FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"stat": {"type": "string"}, "text": {"type": "string"}},
                "required": ["stat", "text"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["findings"],
    "additionalProperties": False,
}


def find_findings(ir: dict, verbatim: bool = False) -> list[dict]:
    """The document's concrete findings — facts/figures/statistics — as up to 10
    {stat, text} pairs. `verbatim` (analyze tier) quotes the document's exact
    numbers and wording; otherwise (generate tier) wording may be tightened.
    Never invents figures. AI-only: heuristics can't do this well."""
    title = (ir.get("title") or "").strip()
    mode_instr = (
        "Quote the document's figures and statements VERBATIM — use its exact "
        "numbers and wording; do not paraphrase, round, or reword."
        if verbatim else
        "Use the document's figures and statements; you may tighten the wording "
        "for clarity, but never invent or alter numbers."
    )
    user = (
        f"Document title: {title}\n\n"
        f"Document content:\n{_doc_text(ir)}\n\n"
        "Extract up to 10 of the document's most striking concrete FINDINGS — "
        "facts, figures, statistics, and quantified outcomes a reader would "
        "remember. Each finding is an object with:\n"
        '  • stat — the headline figure (e.g. "47%", "$2.3M", "3x", "1 in 5"); '
        "an empty string if the finding genuinely has no clean number.\n"
        '  • text — the finding phrased as a fact ("of neighborhoods saw literacy '
        'gains over five years"), NOT as "the report found…". It should read '
        "naturally right after the stat; if there is no stat, make text a complete "
        "sentence.\n"
        f"{mode_instr}\n"
        "Prefer findings that carry a number; order them by impact."
    )
    return complete_json(FINDINGS_SYSTEM, user, _FINDINGS_SCHEMA)["findings"][:10]


def _degenerate(text: str) -> bool:
    """True when a model summary has collapsed into fragment/word-salad — the
    ".. science.. potential.. for every child.." failure mode. Lets us retry
    instead of shipping the brain-fart."""
    if not text:
        return False
    if text.count("..") >= 4:
        return True
    frags = [f.strip() for f in re.split(r"[.!?]+", text) if f.strip()]
    if frags:
        shortish = sum(1 for f in frags if len(f.split()) <= 2)
        if shortish >= 5 or shortish / len(frags) >= 0.4:
            return True
    return False


def generate_summary_variant(ir: dict, style: str, length: str) -> str:
    """Lazy pass: one executive-summary variant for a given (style, length).
    Retries a couple of times if the model degenerates into word-salad, and
    returns "" rather than shipping garbage (the caller/UI then shows nothing)."""
    style = style if style in STYLES else DEFAULT_STYLE
    length = length if length in LENGTHS else DEFAULT_LENGTH
    title = (ir.get("title") or "").strip()
    user = (
        f"Document title: {title}\n\n"
        f"Document content:\n{_doc_text(ir)}\n\n"
        'Write ONE executive-summary variant of this document as JSON {"summary": "..."}.\n'
        f"Voice: {STYLES[style]}\n"
        f"Length: {LENGTHS[length]}\n"
        "Be accurate to the document; do not invent facts, numbers, or names."
    )
    text = ""
    for _ in range(3):
        text = (complete_json(SYSTEM, user, _VARIANT_SCHEMA).get("summary") or "").strip()
        if not _degenerate(text):
            return text
    return ""   # persistent brain-fart — better nothing than garbage
