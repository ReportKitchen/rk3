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


def _toc(body) -> list[dict]:
    items = []
    for h in _walk(body):
        if h.get("type") != "heading":
            continue
        level = h.get("level", 1)
        if level <= 1:  # level-1 is the document title
            continue
        text = h.get("text", "").strip()
        if text:
            items.append({"text": text, "level": level, "anchor": h.get("id", "")})
    return items


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


def build_default_config(ir: dict) -> dict:
    """ir.json -> default landing page config (an ordered list of blocks)."""
    title = (ir.get("title") or "").strip()
    body = ir.get("body", [])
    blocks: list[dict] = []

    def add(btype: str, props: dict, enabled: bool = True):
        blocks.append({
            "id": f"b{len(blocks) + 1}",
            "type": btype,
            "enabled": enabled,
            "props": props,
        })

    add("title", {"text": title})

    summary = _summary(body)
    add("summary", {"text": summary, "source": "heuristic"}, enabled=bool(summary))

    add("cover", {"src": "pages/page-0001.png", "alt": f"{title} — cover" if title else "Document cover"})

    hero = _largest_figure(body)
    if hero:
        add("hero", {"src": hero["src"], "alt": hero.get("alt") or "Hero image"}, enabled=False)

    add("toc", {"items": _toc(body)})
    add("highlights", {"items": _highlights(body)})
    add("share", {})
    add("download", {"label": "Download the full report (PDF)"})

    return {"version": CONFIG_VERSION, "template": "default", "blocks": blocks}


def build_default_theme(ir: dict) -> dict:
    """System-default look: black-on-white, Public Sans, centered 800px column."""
    return {
        "version": THEME_VERSION,
        "source": "system",
        "contentWidth": 800,
        "vars": {
            "--lp-page-bg": "#f4f4f5",
            "--lp-content-bg": "#ffffff",
            "--lp-text": "#111111",
            "--lp-heading": "#111111",
            "--lp-accent": "#1b4965",
            "--lp-font": "'Public Sans', system-ui, -apple-system, sans-serif",
        },
        "elementColors": {
            "download": {"bg": "#1b4965", "fg": "#ffffff"},
            "highlights": {"bg": "#eef3fa"},
        },
    }
