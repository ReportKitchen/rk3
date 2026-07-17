"""Landing-page archetypes.

Grounded in the design-pattern research (sources/docs/research): nonprofit
report landing pages cluster into a few repeatable information architectures.
We detect the best-fit archetype for a document and assemble its template from
the extracted pieces. The user can switch archetypes anytime.
"""

from rk3.landing.ai import DEFAULT_LENGTH, DEFAULT_STYLE
from rk3.landing.extract import (
    default_doc_summary, extract_pieces, summary_sections)

ARCHETYPES = ("research", "campaign", "annual", "toolkit")
ARCHETYPE_LABELS = {
    "research": "Research Article",
    "campaign": "Campaign / Findings",
    "annual": "Annual Report",
    "toolkit": "Minimal Toolkit",
}


def detect_archetype(ir: dict, name: str = "") -> str:
    """Pick the best-fit archetype from title/filename/structure signals."""
    text = f"{name} {ir.get('title', '')}".lower()
    npages = len(ir.get("pages", {}) or {})
    has = lambda *ks: any(k in text for k in ks)

    if has("annual report", "impact report", "annual-report", "ir23", "ir24",
           "impact 20") or ("annual" in text and "report" in text):
        return "annual"
    if has("survey", "state of the", "findings", "poll", "census", "barometer"):
        return "campaign"
    if has("toolkit", "guide", "playbook", "handbook", "how to", "tips",
           "worksheet", "curriculum", "checklist") and npages <= 24:
        return "toolkit"
    return "research"


# ---- block constructors (id assigned later) ----
def _title(p):
    return {"type": "title", "props": {**p["title_pieces"]}}

def _summary_props(p, heading=""):
    # the default AI summary (style + length); the variants map is served
    # separately (block-defaults) and drives the editor's Style/Length switch
    d = p["ai_default"]
    return {"text": d["text"], "style": d["style"], "length": d["length"], "heading": heading}


def _summary(p, heading=""):
    if not p["summary"]:
        return None
    return {"type": "summary", "props": _summary_props(p, heading)}


def _doc_summary_props(p, heading="", media=None):
    ds = p["doc_summary"]
    return {"heading": heading or ds["heading"], "sectionId": ds["sectionId"],
            "blocks": ds["blocks"], "media": media or [], "floatTop": 0}

def _doc_summary(p, heading="", with_cover=False):
    # the verbatim Document Summary; an optional cover sits in its media slot
    # (floated, text wrapping) — the prime visual pattern
    media = [_cover(p)] if with_cover else []
    return {"type": "docSummary", "props": _doc_summary_props(p, heading, media)}

def _summary_region(p, heading="", floated_cover=False):
    """The summary area: a whole verbatim section (Document Summary) when one was
    found, else the short heuristic/AI summary. Returns a list of blocks so the
    no-section fallback can still place a separate cover."""
    if p["summary_sections"]:
        return [_doc_summary(p, heading, with_cover=floated_cover)]
    blocks = [_summary(p, heading)]
    if floated_cover:
        blocks.insert(0, _cover(p))
    return blocks

def _cover(p):
    alt = f"{p['title']} — cover" if p["title"] else "Document cover"
    return {"type": "cover", "props": {"src": p["cover_src"], "alt": alt}}

def _toc(p):
    return {"type": "toc", "props": {"items": p["toc"]}} if p["toc"] else None

def _highlights(p, heading="Highlights"):
    if not p["highlights"]:
        return None
    return {"type": "highlights", "props": {"items": p["highlights"], "heading": heading, "bgColor": "#eef3fa"}}

def _share():
    return {"type": "share", "props": {}}

def _download():
    return {"type": "download", "props": {
        "label": "Download the full report (PDF)", "bgColor": "#1b4965", "textColor": "#ffffff"}}

def _secondary(label):
    return {"type": "secondaryCta", "props": {"label": label, "url": "", "bgColor": "#ffffff", "textColor": "#1b4965"}}


# ---- archetype templates (the recurring information architectures) ----
def _research(p):
    return [_title(p), *_summary_region(p, "Executive summary", floated_cover=True), _toc(p), _download(), _share()]

def _campaign(p):
    return [_title(p), *_summary_region(p), _highlights(p, "Key findings"), _download(), _secondary("Subscribe for updates"), _share()]

def _annual(p):
    return [_title(p), *_summary_region(p, floated_cover=True), _highlights(p, "Impact highlights"), _secondary("Donate"), _download()]

def _toolkit(p):
    return [_title(p), *_summary_region(p), _download()]

TEMPLATES = {"research": _research, "campaign": _campaign, "annual": _annual, "toolkit": _toolkit}


# ---- guidance-driven default page (the content-first redesign) --------------
# The guidance engine (rk3/landing/guidance.py) decides which blocks earn a place
# and in what order; we assemble them from the extracted pieces, preferring the
# guidance's own stats (better than the heuristic findings) and its top-ranked
# story for the new Storytelling block.

def _findings_from_guidance(p, g):
    stats = g.get("stats") or []
    items = [{"stat": s["value"], "text": s["fact"]} for s in stats] or p["findings"]
    if not items:
        return None
    return {"type": "findings", "props": {"items": items, "heading": "What the research shows"}}


def _story_block(g):
    stories = g.get("stories") or []
    if not stories:
        return None
    s = next((x for x in stories if x.get("strength") == "strongest"), stories[0])
    # verbatim quote/narrative enrichment is a follow-up; for now the guidance
    # summary carries the block (subject + kind + what happened)
    return {"type": "storytelling", "props": {
        "subject": s["subject"], "kind": s["kind"], "narrative": s["whatHappened"]}}


_GUIDED = {
    "highlights": lambda p, g: _highlights(p, "Key points"),
    "findings": lambda p, g: _findings_from_guidance(p, g),
    "toc": lambda p, g: _toc(p),
    "storytelling": lambda p, g: _story_block(g),
    "download": lambda p, g: _download(),
    "secondary": lambda p, g: _secondary("Learn more"),
    "share": lambda p, g: _share(),
    "aiSummary": lambda p, g: _summary(p),
}


def build_from_guidance(ir: dict, name: str = "", ai: dict | None = None,
                        guidance: dict | None = None) -> dict:
    """Assemble the default page from the guidance engine's recommendedPage —
    which blocks, in what order, at what length. Title + Cover are page
    fundamentals (Title always; Cover placed per coverLayout). Falls back to the
    archetype builder if guidance is missing."""
    g = (guidance or {}).get("guidance") or {}
    rp = g.get("recommendedPage") or {}
    order = rp.get("blocks") or []
    if not order:
        return build_config(ir, name=name, ai=ai)
    p = _pieces(ir, ai)
    layout = rp.get("coverLayout") or "beside"
    floated_cover = layout in ("beside", "inset") and "execSummary" in order
    blocks = [_title(p)]
    for key in order:
        if key == "execSummary":
            b = (_doc_summary(p, "Executive summary", with_cover=floated_cover)
                 if p["summary_sections"] else _summary(p, "Executive summary"))
        else:
            b = _GUIDED.get(key, lambda p, g: None)(p, g)
        if b:
            blocks.append(b)
    # a standalone cover after the Title when it isn't floated into the summary
    if not floated_cover and layout != "textForward" and p.get("cover_src"):
        blocks.insert(1, _cover(p))
    _assign_ids(blocks)
    return {"version": 1, "template": "guided", "length": rp.get("length", "middle"), "blocks": blocks}


def _pieces(ir: dict, ai: dict | None = None) -> dict:
    """Extracted pieces with the AI content pass layered over the heuristics.
    The AI Summary varies on style × length; ``summary_variants`` is keyed by
    ``"<style>:<length>"`` (the combos generated so far) and drives the editor's
    Style/Length switch, falling back to the heuristic snippet."""
    pieces = extract_pieces(ir)
    variants = dict((ai or {}).get("summaries") or {})  # keyed "style:length"
    if ai:
        if ai.get("title"):
            pieces["title_pieces"] = ai["title"]
        if ai.get("highlights"):
            pieces["highlights"] = ai["highlights"]
        if ai.get("findings"):
            pieces["findings"] = ai["findings"]
        # analyze tier: an AI-identified intro heading lets us pull a verbatim
        # section even when its heading didn't match the keyword patterns
        if ai.get("intro_heading"):
            secs = summary_sections(ir.get("body", []), hints=(ai["intro_heading"],))
            pieces["summary_sections"] = secs
            pieces["doc_summary"] = default_doc_summary(secs, pieces["summary"])
    pieces["summary_variants"] = variants
    default_key = f"{DEFAULT_STYLE}:{DEFAULT_LENGTH}"
    pieces["ai_default"] = {
        "style": DEFAULT_STYLE, "length": DEFAULT_LENGTH,
        # the default combo if AI ran, else the verbatim heuristic snippet
        "text": variants.get(default_key) or pieces["summary"],
    }
    return pieces


def build_config(ir: dict, name: str = "", archetype: str | None = None, ai: dict | None = None) -> dict:
    """Assemble a landing config for the detected (or given) archetype."""
    pieces = _pieces(ir, ai)
    arch = archetype if archetype in TEMPLATES else detect_archetype(ir, name)
    blocks = [b for b in TEMPLATES[arch](pieces) if b]
    _assign_ids(blocks)
    return {"version": 1, "template": arch, "blocks": blocks}


def _assign_ids(blocks) -> None:
    """Assign unique ids across the tree, descending into the media slot so
    nested blocks (a cover inside a Document Summary) are addressable too."""
    counter = [0]

    def walk(bs):
        for b in bs:
            counter[0] += 1
            b["id"] = f"b{counter[0]}"
            media = (b.get("props") or {}).get("media")
            if media:
                walk(media)

    walk(blocks)


def block_defaults(ir: dict, name: str = "", ai: dict | None = None) -> dict:
    """Document-aware default props for every block type, so inserting a block
    from the editor's "+ Add" arrives prepopulated rather than empty."""
    p = _pieces(ir, ai)
    title = (ir.get("title") or "").strip()
    hero = p["hero"]
    return {
        "title": dict(p["title_pieces"]),
        # variants drives the editor's Version switch (stripped before insert)
        "summary": {**_summary_props(p, "Executive summary"), "variants": p["summary_variants"]},
        # sections drives the Document Summary's section picker (stripped on insert)
        "docSummary": {**_doc_summary_props(p), "sections": [
            {"id": s["id"], "heading": s["heading"], "blocks": s["blocks"], "words": s["words"]}
            for s in p["summary_sections"]]},
        "cover": {"src": p["cover_src"], "alt": f"{title} — cover" if title else "Document cover"},
        "hero": ({"src": hero["src"], "alt": hero.get("alt") or "Hero image"}
                 if hero else {"src": "", "alt": "Hero image"}),
        "toc": {"items": p["toc"]},
        "highlights": {"items": p["highlights"], "heading": "Highlights", "bgColor": "#eef3fa"},
        "findings": {"items": p["findings"], "heading": "Key findings"},
        "share": {},
        "download": {"label": "Download the full report (PDF)", "bgColor": "#1b4965", "textColor": "#ffffff"},
        "secondaryCta": {"label": "Learn more", "url": "", "bgColor": "#ffffff", "textColor": "#1b4965"},
    }
