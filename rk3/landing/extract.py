"""Derive a default Landing Page config + theme from a document's IR.

Pure functions: an `ir` dict in, plain dicts out. The web API calls these to
seed defaults the first time a document's Landing Page is opened; the user then
owns and edits the saved config (stored next to the source, like edit ops).

Milestone 1 is deterministic only — no LLM. The `summary` block uses a
heuristic and is tagged ``source: "heuristic"`` so a later AI pass can upgrade
the same slot and label itself.
"""

import re

# headings whose following paragraph tends to be a usable summary/abstract
_SUMMARY_HEADING = re.compile(
    r"\b(abstract|executive\s+summary|summary|overview|introduction)\b", re.I)

CONFIG_VERSION = 1
THEME_VERSION = 1


def _walk(body):
    """Yield every node in reading order, descending into container children
    (aside/columns/deflist) so nested paragraphs and headings are visible."""
    for node in body or []:
        yield node
        kids = node.get("children")
        if kids:
            yield from _walk(kids)


def _trim(text: str, max_chars: int = 400) -> str:
    """Collapse whitespace and cut to a sentence boundary near max_chars."""
    text = " ".join((text or "").split())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    ends = list(re.finditer(r"[.!?]\s", cut))
    if ends:
        return cut[:ends[-1].end()].strip()
    return cut.rsplit(" ", 1)[0].rstrip() + "…"


def _summary(body) -> str:
    seq = list(_walk(body))
    # prefer the first substantial paragraph under a summary-ish heading
    for i, node in enumerate(seq):
        if node.get("type") == "heading" and _SUMMARY_HEADING.search(node.get("text", "")):
            for nxt in seq[i + 1:]:
                if nxt.get("type") == "heading":
                    break
                if nxt.get("type") == "paragraph" and len(nxt.get("text", "")) > 80:
                    return _trim(nxt["text"])
    # else the first reasonably long paragraph anywhere
    paras = [n for n in seq if n.get("type") == "paragraph" and n.get("text")]
    for p in paras:
        if len(p["text"]) >= 120:
            return _trim(p["text"])
    return _trim(paras[0]["text"]) if paras else ""


def _toc(body, limit: int = 8) -> list[dict]:
    """A landing-page 'what's inside', not a full outline. Take only the major
    sections (level 2; fall back to level 3 if there are no level-2 headings)
    and cap the count — nobody wants 185 lines on a landing page."""
    heads = [h for h in _walk(body) if h.get("type") == "heading"]
    for level in (2, 3):
        items = [
            {"text": h.get("text", "").strip(), "level": level, "anchor": h.get("id", "")}
            for h in heads if h.get("level") == level and h.get("text", "").strip()
        ]
        if items:
            return items[:limit]
    return []


def _title_pieces(title: str) -> dict:
    """Split a report title into eyebrow / title / subtitle. Many report titles
    arrive as multiple pieces joined by a colon or pipe, e.g. 'Returns on
    Resilience: Investing in Adaptation to Drive Prosperity'."""
    title = " ".join((title or "").split())
    for sep in (":", "|", " — ", " – "):
        if sep in title:
            head, tail = title.split(sep, 1)
            if head.strip() and tail.strip():
                return {"eyebrow": "", "title": head.strip(), "subtitle": tail.strip()}
    return {"eyebrow": "", "title": title, "subtitle": ""}


def _highlights(body, limit: int = 6) -> list[str]:
    """Best-effort key points: the section headings. Weak without AI, but gives
    the user something to work with; the AI pass replaces this with findings."""
    out = []
    for h in _walk(body):
        if h.get("type") == "heading" and h.get("level") in (2, 3):
            t = h.get("text", "").strip()
            if t and t not in out:
                out.append(t)
    return out[:limit]


def _largest_figure(body):
    figs = [n for n in _walk(body) if n.get("type") == "figure" and n.get("src")]
    if not figs:
        return None
    return max(figs, key=lambda f: (f.get("width") or 0) * (f.get("height") or 0))


def extract_pieces(ir: dict) -> dict:
    """The raw materials a template assembles from. Pure extraction; the
    archetype templates (templates.py) decide which pieces to use and how."""
    title = (ir.get("title") or "").strip()
    body = ir.get("body", [])
    return {
        "title": title,
        "title_pieces": _title_pieces(title),
        "summary": _summary(body),
        "summary_source": "heuristic",
        "toc": _toc(body),
        "highlights": _highlights(body),
        "cover_src": "pages/page-0001.png",
        "hero": _largest_figure(body),
    }


def build_default_theme(ir: dict) -> dict:
    """System-default look: black-on-white, Public Sans, centered 800px column.

    Page-wide values only; per-element colors live on the blocks themselves."""
    return {
        "version": THEME_VERSION,
        "source": "system",
        "contentWidth": 800,
        "vars": {
            "--lp-page-bg": "#ffffff",
            "--lp-content-bg": "#ffffff",
            "--lp-text": "#111111",
            "--lp-heading": "#111111",
            "--lp-accent": "#1b4965",
            "--lp-font": "'Public Sans', system-ui, -apple-system, sans-serif",
        },
    }
