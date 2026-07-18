"""Derive a default Landing Page config + theme from a document's IR.

Pure functions: an `ir` dict in, plain dicts out. The web API calls these to
seed defaults the first time a document's Landing Page is opened; the user then
owns and edits the saved config (stored next to the source, like edit ops).

Milestone 1 is deterministic only — no LLM. The `summary` block uses a
heuristic and is tagged ``source: "heuristic"`` so a later AI pass can upgrade
the same slot and label itself.
"""

import re

from .. import irwalk

# headings whose following paragraph tends to be a usable summary/abstract
_SUMMARY_HEADING = re.compile(
    r"\b(abstract|executive\s+summary|summary|overview|introduction)\b", re.I)

# section-intro headings, with a priority (higher = stronger intro signal). Used
# to pull a whole verbatim section ("Document Summary"), not just a snippet.
_DOC_NOUN = (r"(report|study|document|toolkit|guide|guidebook|playbook|handbook|"
             r"brief|paper|book|project|work|series|publication|initiative|case\s+study)")
_SECTION_PATTERNS = [
    (re.compile(r"\bexecutive\s+summary\b", re.I), 6),
    (re.compile(r"\babstract\b", re.I), 5),
    (re.compile(rf"\babout\s+(this|the|our)\s+{_DOC_NOUN}\b", re.I), 5),
    (re.compile(r"\b(introduction|foreword|preface)\b", re.I), 4),
    (re.compile(r"\b(overview|summary|background)\b", re.I), 2),
]
# headings that look like captions / back-matter, never an intro section
_SKIP_HEADING = re.compile(
    r"^\s*(figure|table|appendix|references|bibliography|acknowledg|notes?\b|endnotes|index)", re.I)

CONFIG_VERSION = 1
THEME_VERSION = 1


def _walk(body):
    """Every node in reading order, all depths (shared walker)."""
    yield from irwalk.walk(body)


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


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _item_texts_of(node):
    """A list node's item texts, for both IR shapes: legacy `items`
    (strings/runs-dicts) and the unified container shape (item nodes whose
    first text leaf carries the item's text)."""
    for it in node.get("items") or []:
        yield (it.get("text", "") if isinstance(it, dict) else str(it)).strip()
    for it in node.get("children") or []:
        leaf = next((ch.get("text", "") for ch in (it.get("children") or [])
                     if ch.get("text")), "")
        yield leaf.strip()


def _item_leaves_of(node):
    """Each list item's first text-bearing leaf node, so callers can weave its
    inline formatting (not just its plain text)."""
    for it in node.get("children") or []:
        leaf = next((ch for ch in (it.get("children") or []) if ch.get("text")), None)
        if leaf:
            yield leaf
    for it in node.get("items") or []:   # legacy string/dict items
        txt = (it.get("text", "") if isinstance(it, dict) else str(it)).strip()
        if txt:
            yield {"text": txt}


# trademark/service marks the extractor recovered as plain letters or glyphs,
# in trademark position — superscript so they look right
def _marks_to_sup(s: str) -> str:
    s = re.sub(r"(?<=[A-Za-z])(™|®|℠)", r"<sup>\1</sup>", s)
    s = re.sub(r"(?<=[a-z])(TM|SM)(?=[^A-Za-z]|$)", r"<sup>\1</sup>", s)
    return s


def _weave(node) -> str:
    """Inline HTML for a text node: keep bold/italic (and any superscripts),
    drop footnote-reference markers (the report's own <sup> numbers, which read
    as stray digits on a landing page). Links are left as plain text — a summary
    has nowhere for the report's internal anchors to point.

    A segment sweep splits the text at every emphasis boundary and re-opens
    spans across boundaries, so overlaps stay well-formed and nothing is dropped
    but the footnote refs."""
    text = node.get("text") or ""
    n = len(text)
    if n == 0:
        return ""
    drop = bytearray(n)  # 1 = a footnote-ref character, removed from the output
    for s, e, *_ in (node.get("refs") or []):
        for i in range(max(0, s), min(n, e)):
            drop[i] = 1
    wraps = []  # (start, end, rank, open, close) — lower rank nests outermost
    for s, e, *_ in (node.get("sups") or []):
        wraps.append((max(0, s), min(n, e), 0, "<sup>", "</sup>"))
    for s, e, kind in (node.get("emph") or []):
        if kind in ("strong", "em"):
            wraps.append((max(0, s), min(n, e), 1 if kind == "strong" else 2,
                          f"<{kind}>", f"</{kind}>"))
    wraps = [w for w in wraps if w[0] < w[1]]

    def seg(a, b):
        return _marks_to_sup(_esc("".join(text[j] for j in range(a, b) if not drop[j])))

    if not wraps:
        return seg(0, n)
    bounds = sorted({0, n} | {b for w in wraps for b in (w[0], w[1])})
    out = []
    for a, b in zip(bounds, bounds[1:]):
        piece = seg(a, b)
        if not piece:
            continue
        active = sorted((w for w in wraps if w[0] <= a and w[1] >= b), key=lambda w: w[2])
        out.append("".join(w[3] for w in active) + piece
                   + "".join(w[4] for w in reversed(active)))
    return "".join(out)


def _flat(body):
    """Reading-order walk that does NOT descend into figures/asides (their inner
    text is caption/label noise, not part of a readable section). Lists and
    tables are structured containers — yielded whole, never entered (their
    leaf paragraphs are the container's content, not free-standing text)."""
    yield from irwalk.walk(body, skip=("aside", "figure", "footnotes"),
                           prune=("list", "table"))


def _section_blocks(nodes) -> list[str]:
    """A section's nodes as a list of block-level HTML chunks (paragraphs, its
    sub-headings, lists). A list — not one blob — so the editor can place a
    floated image *between* blocks, letting the text above it run full-width and
    the text below wrap around it. Figures/asides are excluded by _flat."""
    out = []
    for n in nodes:
        t = n.get("type")
        text = (n.get("text") or "").strip()
        if t == "paragraph" and text:
            out.append(f"<p>{_weave(n)}</p>")
        elif t == "heading" and text and not _SKIP_HEADING.match(text):
            lvl = min(max(n.get("level", 3), 3), 4)  # sub-headings → h3/h4
            out.append(f"<h{lvl}>{_weave(n)}</h{lvl}>")
        elif t == "list":
            lis = "".join(f"<li>{w}</li>" for w in map(_weave, _item_leaves_of(n)) if w)
            if lis:
                # keep the source's list kind (ordered vs bulleted) and its start
                if n.get("ordered"):
                    start = n.get("start")
                    attr = f' start="{start}"' if isinstance(start, int) and start != 1 else ""
                    out.append(f"<ol{attr}>{lis}</ol>")
                else:
                    out.append(f"<ul>{lis}</ul>")
    return out


def _section_priority(text: str) -> int:
    for pat, score in _SECTION_PATTERNS:
        if pat.search(text):
            return score
    return 0


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def extract_summary_sections(body, max_sections: int = 4, min_chars: int = 200,
                             hints: tuple = ()) -> list[dict]:
    """Whole verbatim intro/summary sections for the Document Summary element.

    Find headings that look like an intro (executive summary / abstract / about /
    introduction / overview…) and take the ENTIRE section — every node until the
    next heading of equal-or-higher rank — as semantic HTML. Rank candidates so a
    real 'Executive Summary' beats a chapter's 'Overview' subsection.

    `hints` are heading texts the AI analyze pass identified as the intro section.
    Their sections are included even when the heading doesn't match the keyword
    patterns (the point of analyze: non-standard headings) and rank first."""
    seq = list(_flat(body))
    heads = [(i, n) for i, n in enumerate(seq) if n.get("type") == "heading"]
    hint_set = {_norm(h) for h in hints}
    out = []
    for k, (i, h) in enumerate(heads):
        text = (h.get("text") or "").strip()
        if _SKIP_HEADING.match(text):
            continue
        # substring match: an AI hint heading ("EXECUTIVE SUMMARY") should also
        # match near-duplicates like "I. Executive Summary" (and pick whichever
        # yields the most content, via the min_chars filter + ranking)
        nt = _norm(text)
        is_hint = any(hn and (hn in nt or nt in hn) for hn in hint_set)
        prio = _section_priority(text)
        if not prio and not is_hint:
            continue
        level = h.get("level", 1)
        if level >= 5 and not is_hint:  # deep "headings" are usually running-header artifacts
            continue
        # the section runs until the next heading of equal-or-higher rank
        end = len(seq)
        for j, n2 in heads:
            if j > i and n2.get("level", 99) <= level:
                end = j
                break
        blocks = _section_blocks(seq[i + 1:end])
        plain = re.sub("<[^>]+>", "", " ".join(blocks))
        chars = len(plain)
        if chars < min_chars:
            continue
        words = len(plain.split())
        # weak keywords (overview/summary/background) only count near the front
        # and at a top level, where they're plausibly the document's intro
        front = i <= len(seq) * 0.5
        if prio <= 2 and not is_hint and not (front and level <= 2):
            continue
        out.append({
            "heading": text, "anchor": h.get("id", ""), "level": level,
            "blocks": blocks, "chars": chars, "words": words,
            # an AI-identified section ranks above all keyword matches
            "_score": (10000 if is_hint else prio * 1000) + max(0, 1000 - i),
        })
    out.sort(key=lambda s: s["_score"], reverse=True)
    # dedupe repeated headers (e.g. a running header misread as a heading)
    seen, deduped = set(), []
    for s in out:
        key = re.sub(r"[^a-z0-9]+", "", s["heading"].lower())
        if key in seen:
            continue
        seen.add(key)
        del s["_score"]
        deduped.append(s)
    return deduped[:max_sections]


def summary_sections(body, hints: tuple = ()) -> list[dict]:
    """The Document Summary's section candidates, each with a stable id."""
    return [{"id": f"s{i}", **s} for i, s in enumerate(extract_summary_sections(body, hints=hints))]


def default_doc_summary(sections: list[dict], snippet: str) -> dict:
    """The Document Summary's default content: the top-ranked section, else the
    short heuristic snippet wrapped as a paragraph (still verbatim)."""
    if sections:
        s0 = sections[0]
        return {"heading": s0["heading"], "sectionId": s0["id"], "blocks": s0["blocks"]}
    return {"heading": "Summary", "sectionId": "",
            "blocks": [f"<p>{_esc(snippet)}</p>"] if snippet else []}


def _toc(body, limit: int = 8, title: str = "", min_count: int = 3) -> list[dict]:
    """A landing-page 'what's inside', not a full outline. The major-section
    level varies by document — some use H1 for sections and H2 for the subtitle,
    others the reverse — so don't hardcode level 2 (which returned a single item
    on docs whose sections are H1). Pick the SHALLOWEST level that has enough
    headings to be a real section series, drop back-matter and the doc title,
    and cap the count."""
    heads = [h for h in _walk(body)
             if h.get("type") == "heading" and h.get("text", "").strip()
             and not _SKIP_HEADING.match(h.get("text", ""))]
    tnorm = _norm(title)
    by_level: dict[int, list] = {}
    for h in heads:
        # skip the document title itself when it appears as a heading
        hnorm = _norm(h.get("text", ""))
        if tnorm and hnorm and (hnorm == tnorm or (len(hnorm) >= 8 and tnorm.startswith(hnorm))):
            continue
        by_level.setdefault(h.get("level", 99), []).append(h)
    if not by_level:
        return []
    # shallowest (most major) level with a real series; else the most populous
    chosen = next((lvl for lvl in sorted(by_level) if len(by_level[lvl]) >= min_count), None)
    if chosen is None:
        chosen = max(by_level, key=lambda lvl: len(by_level[lvl]))
    return [
        {"text": h.get("text", "").strip(), "level": chosen, "anchor": h.get("id", "")}
        for h in by_level[chosen]
    ][:limit]


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
    snippet = _summary(body)
    sections = summary_sections(body)
    return {
        "title": title,
        "title_pieces": _title_pieces(title),
        "summary": snippet,
        "summary_source": "heuristic",
        "summary_sections": sections,  # whole verbatim intro sections, each id'd
        "doc_summary": default_doc_summary(sections, snippet),
        "toc": _toc(body, title=title),
        "highlights": _highlights(body),
        "findings": [],  # AI-only (filled by the AI pass); heuristics can't do this
        "cover_src": "pages/page-0001.png",
        "hero": _largest_figure(body),
    }


# system stack on purpose — no web-font dependency for the exported page
_DEFAULT_FONT = "Helvetica, Verdana, sans-serif"


def build_default_theme(ir: dict) -> dict:
    """System-default look: black-on-white, system sans, centered 800px column.

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
            "--lp-h2-color": "#111111",
            "--lp-font": _DEFAULT_FONT,
        },
    }


def theme_from_scan(scan: dict) -> dict:
    """Map a webscan PageStyle (rk3.webscan.scan_page) to a landing theme, to
    pre-fill Page setup from the client's own published page. Same shape as
    build_default_theme; falls back to the system defaults field by field so a
    partial scan still yields a usable theme."""
    c = scan.get("content") or {}
    layout = scan.get("layout") or {}
    link = c.get("link") or {}
    heading = c.get("heading") or {}
    sidebar = layout.get("sidebar") or {}

    # snap the measured column to the width slider's range + step (600-1200 / 20)
    width = c.get("width") or 800
    width = max(600, min(1200, round(width / 20) * 20))

    side = sidebar.get("side") if sidebar.get("present") else None
    return {
        "version": THEME_VERSION,
        "source": "scan",
        "contentWidth": width,
        "vars": {
            "--lp-page-bg": (scan.get("page") or {}).get("bg") or "#ffffff",
            "--lp-content-bg": c.get("bg") or "#ffffff",
            "--lp-text": c.get("textColor") or "#111111",
            "--lp-heading": heading.get("color") or c.get("textColor") or "#111111",
            "--lp-accent": link.get("color") or "#1b4965",
            # captured for the export; the editor doesn't apply it yet (font is
            # not a themeable field), so a scanned page still renders in the
            # default face until font threading lands
            "--lp-font": c.get("fontStack") or _DEFAULT_FONT,
        },
        "preview": {
            "leftSidebar": side == "left",
            "rightSidebar": side == "right",
        },
    }
