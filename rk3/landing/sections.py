"""AI content sections — the block-model reframe (sources/docs/BACKLOG/61).

The AI reads a converted document and proposes the meaningful, doc-specific
SECTIONS a landing page should carry — each with the document's OWN heading and
words, and a presentation primitive (prose / bullets / statCards / quote / steps).
This replaces the fixed highlights/findings/etc. catalog and the advisor↔author
split (the note and the content now come from ONE pass, so they can't disagree).

Verbatim-first is the load-bearing rule (RK3 mantra: "feels just like my
document"). Prompts live in the content registry (shared.analysis.sections_*); the
JSON schema is the code contract and stays here.

Two tiers, same as guidance:
  1. PROFILE — deterministic, reused from guidance.profile()
  2. SECTIONS — one grounded AI call (verbatim selection into primitives)

A functional no-AI fallback (extract the exec summary + canned placeholder
sections) keeps the feature usable when AI is off — the AI path is the star.
"""
from rk3 import content
from rk3.ai import complete_json
from rk3.landing import guidance
from rk3.landing.extract import extract_pieces


# ---- content shapes per presentation primitive (strict schema: every field
# required; the model fills only the one matching `presentation`, leaves the rest
# empty) ----
_PRESENTATIONS = ["prose", "bullets", "statCards", "quote", "steps"]
_STRENGTHS = ["strongest", "solid", "thin"]

_CARD = {"type": "object", "additionalProperties": False,
         "required": ["value", "label"],
         "properties": {"value": {"type": "string"}, "label": {"type": "string"}}}
_STEP = {"type": "object", "additionalProperties": False,
         "required": ["label", "body"],
         "properties": {"label": {"type": "string"}, "body": {"type": "string"}}}
_QUOTE = {"type": "object", "additionalProperties": False,
          "required": ["text", "attribution", "pull"],
          "properties": {"text": {"type": "string"}, "attribution": {"type": "string"},
                         "pull": {"type": "boolean"}}}

_SECTION = {
    "type": "object", "additionalProperties": False,
    "required": ["heading", "summary", "role", "presentation", "page", "strength",
                 "verbatim", "prose", "bullets", "cards", "quote", "steps"],
    "properties": {
        "heading": {"type": "string"},
        "summary": {"type": "string"},
        # intro = the document's own front-matter (foreword/introduction/exec
        # summary/overview); body = everything else. Drives a separate UI group.
        "role": {"type": "string", "enum": ["intro", "body"]},
        "presentation": {"type": "string", "enum": _PRESENTATIONS},
        "page": {"type": "string"},
        "strength": {"type": "string", "enum": _STRENGTHS},
        "verbatim": {"type": "boolean"},
        "prose": {"type": "string"},
        "bullets": {"type": "array", "items": {"type": "string"}},
        "cards": {"type": "array", "items": _CARD},
        "quote": _QUOTE,
        "steps": {"type": "array", "items": _STEP},
    },
}

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["documentRead", "recommendedPage", "sections"],
    "properties": {
        "documentRead": {"type": "object", "additionalProperties": False,
                         "required": ["whatItIs", "audience", "coreMessage"],
                         "properties": {k: {"type": "string"} for k in ("whatItIs", "audience", "coreMessage")}},
        "recommendedPage": {"type": "object", "additionalProperties": False,
                            "required": ["length", "cover"],
                            "properties": {"length": {"type": "string", "enum": ["short", "middle", "long"]},
                                           "cover": {"type": "string", "enum": ["onTop", "beside", "inset", "textForward"]}}},
        "sections": {"type": "array", "items": _SECTION},
    },
}


def generate(ir: dict) -> dict:
    """Run the AI sections pass. Returns {profile, sections}. Raises on any AI
    error — the caller decides whether to cache, retry, or drop to the fallback."""
    p = guidance.profile(ir)
    system, model = content.prompt("shared.analysis.sections_system")
    catalog, _ = content.prompt("shared.analysis.presentation_catalog")
    task, _ = content.prompt("shared.analysis.sections_task")
    user = (
        f"Document title: {p['title']}\n"
        f"Length: {p['pages']} pages, ~{p['approxWords']} words. "
        f"Its intro/summary section runs ~{p['introSectionWords']} words.\n\n"
        f"{catalog}\n\nFULL DOCUMENT:\n{guidance._full_text(ir)}\n\n{task}"
    )
    data = complete_json(system, user, SCHEMA, max_tokens=8000, model=model)
    return {"profile": p, "sections": data}


def _empty_content() -> dict:
    """The zero value for every primitive's content field (fill the one you use)."""
    return {"prose": "", "bullets": [], "cards": [],
            "quote": {"text": "", "attribution": "", "pull": False}, "steps": []}


def _section(heading, summary, presentation, *, verbatim, strength, role="body", page="", **content_over) -> dict:
    s = {"heading": heading, "summary": summary, "role": role, "presentation": presentation,
         "page": page, "strength": strength, "verbatim": verbatim}
    s.update(_empty_content())
    s.update(content_over)
    return s


def fallback(ir: dict) -> dict:
    """No-AI functional version: the report's own exec summary as a prose section,
    plus a couple of canned placeholder sections for the user to fill. Degraded but
    usable — the AI path is the star."""
    p = extract_pieces(ir)
    prof = guidance.profile(ir)
    sections = []
    ds = p.get("doc_summary") or {}
    blocks = ds.get("blocks") or []
    heading = ds.get("heading") or content.text("shared.analysis.noai.intro_heading")
    if blocks:
        sections.append(_section(heading, "", "prose", role="intro", verbatim=True,
                                 strength="strongest", prose="".join(blocks)))
    elif p.get("summary"):
        sections.append(_section(heading, "", "prose", role="intro", verbatim=True,
                                 strength="solid", prose=f"<p>{p['summary']}</p>"))
    # canned placeholders — real recommendations, empty content for the user to fill
    sections.append(_section(content.text("shared.analysis.noai.findings.heading"),
                             content.text("shared.analysis.noai.findings.note"),
                             "statCards", verbatim=False, strength="thin"))
    sections.append(_section(content.text("shared.analysis.noai.story.heading"),
                             content.text("shared.analysis.noai.story.note"),
                             "quote", verbatim=False, strength="thin"))
    return {
        "profile": prof,
        "sections": {
            "documentRead": {"whatItIs": prof.get("title", ""), "audience": "", "coreMessage": ""},
            "recommendedPage": {"length": "middle", "cover": "beside"},
            "sections": sections,
        },
        "noai": True,
    }
