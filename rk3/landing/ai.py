"""AI content pass for the Landing Page Maker.

Given a document's IR, generate higher-quality starter content than the
deterministic heuristics can: a multi-piece title, executive-summary variants,
and genuine key findings. Grounded in the document text; the model is told not
to invent facts. Falls back to heuristics on any error (see callers).

Summaries vary on two axes — voice (STYLES) and length (LENGTHS). The upfront
pass generates the three styles at the default length in one call; other
(style, length) combinations are generated lazily, on demand, and cached.
"""

from rk3.ai import complete_json
from rk3.landing.extract import _walk

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

SYSTEM = (
    "You write concise, compelling copy for a nonprofit or research report "
    "landing page. The copy appears on the publishing organization's own "
    "website. Work only from the provided document — be accurate and do not "
    "invent facts, statistics, names, or findings; prefer the document's own "
    "framing and numbers."
)

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


def generate_summary_variant(ir: dict, style: str, length: str) -> str:
    """Lazy pass: one executive-summary variant for a given (style, length)."""
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
    return complete_json(SYSTEM, user, _VARIANT_SCHEMA)["summary"]
