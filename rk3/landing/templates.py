"""Landing-page archetypes.

Grounded in the design-pattern research (sources/docs/research): nonprofit
report landing pages cluster into a few repeatable information architectures.
We detect the best-fit archetype for a document and assemble its template from
the extracted pieces. The user can switch archetypes anytime.
"""

from rk3.landing.extract import _walk, extract_pieces

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

def _summary(p, heading=""):
    if not p["summary"]:
        return None
    return {"type": "summary", "props": {
        "text": p["summary"], "source": p.get("summary_source", "heuristic"), "heading": heading}}

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
    return [_title(p), _summary(p, "Executive summary"), _cover(p), _toc(p), _download(), _share()]

def _campaign(p):
    return [_title(p), _summary(p), _highlights(p, "Key findings"), _download(), _secondary("Subscribe for updates"), _share()]

def _annual(p):
    return [_title(p), _cover(p), _highlights(p, "Impact highlights"), _summary(p), _secondary("Donate"), _download()]

def _toolkit(p):
    return [_title(p), _summary(p), _download()]

TEMPLATES = {"research": _research, "campaign": _campaign, "annual": _annual, "toolkit": _toolkit}


def build_config(ir: dict, name: str = "", archetype: str | None = None, ai: dict | None = None) -> dict:
    """Assemble a landing config for the detected (or given) archetype.

    `ai` (when present) is the cached AI content pass; its title/summary/
    highlights replace the deterministic heuristics."""
    pieces = extract_pieces(ir)
    if ai:
        if ai.get("title"):
            pieces["title_pieces"] = ai["title"]
        if ai.get("summary"):
            pieces["summary"] = ai["summary"]
            pieces["summary_source"] = "ai"
        if ai.get("highlights"):
            pieces["highlights"] = ai["highlights"]
    arch = archetype if archetype in TEMPLATES else detect_archetype(ir, name)
    blocks = [b for b in TEMPLATES[arch](pieces) if b]
    for i, b in enumerate(blocks, 1):
        b["id"] = f"b{i}"
    return {"version": 1, "template": arch, "blocks": blocks}
