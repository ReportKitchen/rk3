"""AI content pass for the Landing Page Maker.

Given a document's IR, generate higher-quality starter content than the
deterministic heuristics can: a multi-piece title, a real executive summary,
and genuine key findings. Grounded in the document text; the model is told not
to invent facts. Falls back to heuristics on any error (see callers).
"""

from rk3.ai import complete_json
from rk3.landing.extract import _walk

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
        "summary": {"type": "string"},
        "highlights": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "summary", "highlights"],
    "additionalProperties": False,
}

SYSTEM = (
    "You write concise, compelling copy for a nonprofit or research report "
    "landing page. Work only from the provided document — be accurate and do "
    "not invent facts, statistics, names, or findings. Prefer the document's "
    "own framing and numbers."
)


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
    """Returns {title: {eyebrow,title,subtitle}, summary: str, highlights: [str]}."""
    title = (ir.get("title") or "").strip()
    user = (
        f"Document title: {title}\n\n"
        f"Document content:\n{_doc_text(ir)}\n\n"
        "Produce, as JSON:\n"
        "1. title — split the report title into: eyebrow (a short kicker/category "
        "or series name; may be empty), title (the main title), subtitle (the deck "
        "or descriptive sub-line; may be empty). Use the real title pieces; don't pad.\n"
        "2. summary — a 2–3 sentence executive summary (~40–60 words) of what the "
        "document says and why it matters.\n"
        "3. highlights — 3–5 key findings as short, concrete bullet strings a reader "
        "would care about (outcomes, numbers, conclusions), each grounded in the document."
    )
    return complete_json(SYSTEM, user, SCHEMA)
