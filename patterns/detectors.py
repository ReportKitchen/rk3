"""Deterministic Stage A candidate detection.

The IR already types the structural content. This module consumes those typed
nodes via rk3.irwalk and only code-detects inline signals the IR does not type.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from typing import Any

from rk3 import irwalk


NUMBER_RE = re.compile(
    r"(?P<value>(?:[$][ ]?)?\d[\d,]*(?:\.\d+)?(?:[ ]?(?:%|percent|percentage points|million|billion|thousand))?)",
    re.I,
)
DATE_RE = re.compile(
    r"\b(?:"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},?\s+\d{4}|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{4}|"
    r"(?:19|20)\d{2}(?:\s*[-/]\s*(?:19|20)?\d{2})?"
    r")\b"
)
QUOTE_RE = re.compile(r"""["'“‘](?P<quote>[^"'”’]{24,500})["'”’]""")
QUESTION_RE = re.compile(r"(^|[.!?]\s+)(?P<question>[^.!?]{8,220}\?)")
LABEL_VALUE_RE = re.compile(r"^\s*(?P<label>[^:]{2,80}):\s*(?P<value>.+?)\s*$")
DEFINITION_RE = re.compile(
    r"""\b(?P<term>[A-Za-z][A-Za-z0-9 /"'“”‘’-]{2,80}?)"""
    r"\s*(?:,?\s+which means|means|refers to|is defined as|known as)\s+"
    r"(?P<definition>[^.]{3,240})",
    re.I,
)
WHICH_MEANS_RE = re.compile(
    r"[\"'“‘]?(?P<term>[A-Za-z][A-Za-z -]{2,60}),?[\"'”’]?\s+which means\s+(?P<definition>[^,.;]{2,120})",
    re.I,
)
QUESTION_PROMPT_RE = re.compile(r"^(what|who|when|where|why|how|which)\b.{8,140}$", re.I)
RECOMMENDATION_RE = re.compile(r"\b(should|must|need to|needs to|recommend|increase|fund|create|adopt|require|expand|establish|invest|coordinate|evaluate)\b", re.I)
KEY_FINDING_RE = re.compile(r"\b(key finding|finding|we find|this shows|this demonstrates|evidence suggests)\b", re.I)
ACTION_START_RE = re.compile(r"^\s*(partner|connect|collaborate|hold|develop|enlist|increase|fund|create|adopt|require|expand|establish|invest|coordinate|evaluate|seek|seeking|challenge|challenging|negotiate|negotiating|identify|make sure)\b", re.I)
ENTITY_PHRASE_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z&.'’-]+|[A-Z]{2,})(?:\s+(?:[A-Z][A-Za-z&.'’-]+|of|and|for|the|[A-Z]{2,})){1,7}\b"
)
ENTITY_SUFFIXES = {
    "Act", "Agency", "Association", "Center", "Clinic", "Coalition", "College",
    "Commission", "Committee", "Community", "Company", "Council", "Department",
    "Foundation", "Fund", "Health", "Hospital", "Initiative", "Institute",
    "Network", "Partners", "Project", "School", "University",
}
ENTITY_STOPWORDS = {
    "Annual Report", "Board Members", "Case Study", "Executive Summary",
    "Financials", "Key Strategies", "Learn More", "Our Donors", "Table",
}

STATE_NAMES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming", "United States",
}
GEO_RE = re.compile(r"\b(" + "|".join(re.escape(s) for s in sorted(STATE_NAMES, key=len, reverse=True)) + r")\b")


def detect(ir: dict, document_id: str, registry: dict[str, dict]) -> list[dict[str, Any]]:
    body = ir.get("body") or []
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    stats_by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)

    def add(pattern_type: str, node: dict, fields: dict[str, Any], confidence: float, reason: str, quote: str | None = None) -> None:
        if pattern_type not in registry:
            return
        quote_text = clean_quote(quote if quote is not None else node_text(node))
        if not quote_text:
            return
        pid = stable_id(document_id, pattern_type, node.get("nid"), fields)
        if pid in seen:
            return
        seen.add(pid)
        entry = registry[pattern_type]
        candidates.append({
            "pattern_id": pid,
            "pattern_type": pattern_type,
            "pattern_name": entry["name"],
            "layer": entry["layer"],
            "status": "candidate",
            "confidence": round(confidence, 3),
            "detector": "stage_a_deterministic",
            "reason": reason,
            "source_refs": [{
                "nid": node.get("nid"),
                "page": node.get("page"),
                "quote": quote_text,
            }],
            "fields": fields,
            "component_recommendations": recommendations(pattern_type, entry),
            "missing_data_suggestions": [],
            "review": {"status": "unreviewed"},
        })

    leaves = list(irwalk.leaves(body))
    for node in leaves:
        text = node.get("text") or ""
        for match in NUMBER_RE.finditer(text):
            value = match.group("value").strip()
            if should_skip_number(value, text, match.start(), node):
                continue
            unit = infer_unit(text, match.end())
            label = infer_label(text, match.start())
            quote = sentence_around(text, match.start(), match.end())
            add(
                "statistic",
                node,
                {
                    "value": value,
                    "unit": unit,
                    "label": label,
                    "surrounding_claim": quote,
                },
                0.72,
                "Numeric value with possible unit in a text leaf.",
                quote,
            )
            page = node.get("page")
            if isinstance(page, int):
                stats_by_page[page].append({
                    "node": node,
                    "value": value,
                    "unit": unit,
                    "label": label,
                    "quote": quote,
                })

        for match in DATE_RE.finditer(text):
            add(
                "date_time_period",
                node,
                {"value": match.group(0), "context": sentence_around(text, match.start(), match.end())},
                0.78,
                "Date or year expression in a text leaf.",
                sentence_around(text, match.start(), match.end()),
            )

        for match in GEO_RE.finditer(text):
            add(
                "geography_place",
                node,
                {"place": match.group(0), "context": sentence_around(text, match.start(), match.end())},
                0.74,
                "Known U.S. state or national geography mention.",
                sentence_around(text, match.start(), match.end()),
            )

        for ref in node.get("refs") or []:
            marker = ref[2] if len(ref) > 2 else None
            context = ref_context(text, ref)
            add(
                "source_note_reference",
                node,
                {"marker": str(marker), "context": context},
                0.92,
                "IR inline refs run.",
                context,
            )

        if node.get("quoteOpen") or "“" in text or '"' in text:
            for match in QUOTE_RE.finditer(text):
                add(
                    "quotation",
                    node,
                    {"quote_text": match.group("quote").strip(), "speaker_name": None},
                    0.7,
                    "Quotation marks in text leaf.",
                    match.group(0),
                )
            if node.get("quoteOpen") and not any(QUOTE_RE.finditer(text)):
                add(
                    "quotation",
                    node,
                    {"quote_text": text.strip(), "speaker_name": None},
                    0.68,
                    "IR quote-open styling on text leaf.",
                    text,
                )

        found_question = False
        for match in QUESTION_RE.finditer(text):
            found_question = True
            question = match.group("question").strip()
            add(
                "question",
                node,
                {"question_text": question, "answer_context": following_answer(text, question)},
                0.82,
                "Question punctuation in text leaf.",
                question,
            )
        if not found_question:
            prompt = question_like_prompt(node, text)
            if prompt:
                add(
                    "question",
                    node,
                    {"question_text": prompt, "answer_context": following_answer(text, prompt)},
                    0.66,
                    "Question-word prompt in styled lead text.",
                    prompt,
                )

        definition = find_definition(text)
        if definition:
            add(
                "definition",
                node,
                {"term": definition["term"], "definition": definition["definition"]},
                0.62,
                "Definition-like wording in a paragraph.",
                sentence_around(text, definition["start"], definition["end"]),
            )

        if is_recommendation_text(text):
            add(
                "recommendation",
                node,
                {"action": first_sentence(text), "actor": None, "target": None},
                0.55,
                "Action or recommendation verb in a text leaf.",
                first_sentence(text),
            )

        if KEY_FINDING_RE.search(text):
            add(
                "key_finding",
                node,
                {"finding_text": first_sentence(text), "supporting_evidence_refs": []},
                0.58,
                "Finding indicator phrase in a text leaf.",
                first_sentence(text),
            )

    for node in irwalk.of_type(body, "heading"):
        text = clean_entity_text(node.get("text") or "")
        if is_entity_candidate(text, heading=True):
            add(
                "named_entity",
                node,
                {"entity_text": text, "entity_type": infer_entity_type(text), "source": "heading"},
                0.82 if node.get("level", 9) <= 2 else 0.7,
                "Title-case heading with entity-like wording.",
                text,
            )
        if text.lower() in {"stories of impact", "impact", "highlights", "key findings"}:
            add(
                "key_finding",
                node,
                {"finding_text": text, "supporting_evidence_refs": []},
                0.62,
                "Impact/finding heading that signals a summary module.",
                text,
            )

    for node in leaves:
        text = node.get("text") or ""
        for entity in entities_in_text(text):
            add(
                "named_entity",
                node,
                {"entity_text": entity, "entity_type": infer_entity_type(entity), "source": "text"},
                0.66,
                "Entity-like proper noun phrase with organization/program suffix.",
                sentence_containing(text, entity),
            )

    for page, stats in stats_by_page.items():
        usable = dedupe_stats([s for s in stats if s.get("value")])
        strong = [s for s in usable if is_strong_metric_value(s.get("value", ""))]
        if len(usable) >= 2 or strong:
            basis = strong if strong else usable
            first = basis[0]["node"]
            quote = " ".join(unique_texts(s["quote"] for s in basis[:8]))
            add(
                "metric_cluster",
                first,
                {
                    "metrics": [
                        {"label": s.get("label"), "value": s.get("value"), "unit": s.get("unit")}
                        for s in basis[:12]
                    ],
                    "shared_context": f"page {page}",
                },
                0.68 if len(basis) >= 2 else 0.6,
                "Multiple statistic candidates on the same page." if len(basis) >= 2 else "Prominent standalone impact metric.",
                quote,
            )

    for node in irwalk.of_type(body, "aside"):
        text = irwalk.subtree_text(node)
        add(
            "callout",
            node,
            {"callout_text": clean_quote(text), "callout_type": "quote" if node.get("quote") else "sidebar"},
            0.82 if node.get("quote") else 0.66,
            "IR aside container.",
            text,
        )
        if node.get("quote"):
            add(
                "quotation",
                node,
                {"quote_text": clean_quote(text), "speaker_name": None},
                0.76,
                "IR aside marked as quote.",
                text,
            )

    for node in irwalk.of_type(body, "table"):
        text = irwalk.subtree_text(node)
        add(
            "comparison_table",
            node,
            {"table_text": clean_quote(text), "has_header": bool(node.get("header"))},
            0.86,
            "IR table container.",
            text,
        )
        metrics = label_values_from_container(node)
        if len(metrics) >= 2:
            add(
                "metric_cluster",
                node,
                {"metrics": metrics[:12], "shared_context": None},
                0.76,
                "Repeated label/value structures inside a table.",
                text,
            )

    for node in irwalk.of_type(body, "footnotes"):
        for note in node.get("notes") or []:
            text = clean_quote(note.get("text") or "")
            if not text:
                continue
            synthetic = {
                "nid": f"{node.get('nid')}:note:{note.get('marker') or note.get('n')}",
                "page": note.get("page") or node.get("page"),
                "text": text,
            }
            add(
                "source_note_reference",
                synthetic,
                {"marker": str(note.get("marker") or note.get("n")), "context": text, "note_text": text},
                0.88,
                "IR footnote record.",
                text,
            )

    for node in irwalk.of_type(body, "list"):
        item_texts = [irwalk.subtree_text(item) for item in node.get("children") or [] if item.get("type") == "item"]
        question_count = sum(1 for t in item_texts if "?" in t)
        action_count = sum(1 for t in item_texts if is_action_item(t))
        if len(item_texts) >= 2 and question_count >= max(2, len(item_texts) // 2):
            add(
                "question_list",
                node,
                {"questions": item_texts[:20]},
                0.84,
                "Multiple question-like items in an IR list.",
                "\n".join(item_texts),
            )
        elif len(item_texts) >= 3 and (node.get("ordered") or action_count >= 2):
            add(
                "process_step_list",
                node,
                {"steps": item_texts[:20], "ordered": bool(node.get("ordered"))},
                0.7,
                "IR list with ordered or action-oriented items.",
                "\n".join(item_texts),
            )
        metrics = label_values_from_texts(item_texts)
        if len(metrics) >= 2:
            add(
                "metric_cluster",
                node,
                {"metrics": metrics[:12], "shared_context": None},
                0.72,
                "Repeated label/value structures inside a list.",
                "\n".join(item_texts),
            )

    return sorted(candidates, key=lambda c: (c["source_refs"][0].get("page") or 0, c["pattern_type"], c["pattern_id"]))


def inventory(candidates: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(c["pattern_type"] for c in candidates).items()))


def page_inventory(candidates: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    by_page: dict[str, Counter] = defaultdict(Counter)
    for candidate in candidates:
        page = candidate["source_refs"][0].get("page")
        by_page[str(page)][candidate["pattern_type"]] += 1
    return {page: dict(sorted(counts.items())) for page, counts in sorted(by_page.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0)}


def stable_id(document_id: str, pattern_type: str, nid: Any, fields: dict[str, Any]) -> str:
    seed = repr((document_id, pattern_type, nid, fields))
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"patt_{digest}"


def node_text(node: dict) -> str:
    if node.get("text"):
        return node["text"]
    return irwalk.subtree_text(node)


def clean_quote(text: str, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def first_sentence(text: str) -> str:
    match = re.search(r".+?(?:[.!?](?:\s|$)|$)", re.sub(r"\s+", " ", text or "").strip())
    return clean_quote(match.group(0) if match else text, 220)


def sentence_around(text: str, start: int, end: int) -> str:
    left = max(text.rfind(".", 0, start), text.rfind("?", 0, start), text.rfind("!", 0, start))
    right_candidates = [i for i in (text.find(".", end), text.find("?", end), text.find("!", end)) if i != -1]
    right = min(right_candidates) + 1 if right_candidates else min(len(text), end + 120)
    return clean_quote(text[left + 1:right])


def ref_context(text: str, ref: list[Any]) -> str:
    if len(ref) < 2:
        return clean_quote(text)
    context = sentence_around(text, ref[0], ref[1])
    marker = str(ref[2]) if len(ref) > 2 else text[ref[0]:ref[1]]
    if normalize_marker_context(context) == normalize_marker_context(marker):
        return sentence_before(text, ref[0]) or context
    return context


def sentence_before(text: str, offset: int) -> str | None:
    prefix = text[:offset].rstrip()
    if not prefix:
        return None
    end = len(prefix)
    left = max(prefix.rfind(".", 0, max(0, end - 1)), prefix.rfind("?", 0, max(0, end - 1)), prefix.rfind("!", 0, max(0, end - 1)))
    return clean_quote(prefix[left + 1:end])


def normalize_marker_context(text: str) -> str:
    return re.sub(r"\W+", "", text or "")


def find_definition(text: str) -> dict[str, Any] | None:
    which = WHICH_MEANS_RE.search(text or "")
    if which:
        term = which.group("term").strip(" \"'“”‘’")
        if len(term.split()) > 6:
            term = " ".join(term.split()[-6:])
        return {
            "term": term,
            "definition": which.group("definition").strip(),
            "start": which.start(),
            "end": which.end(),
        }
    generic = DEFINITION_RE.search(text or "")
    if generic:
        return {
            "term": generic.group("term").strip(),
            "definition": generic.group("definition").strip(),
            "start": generic.start(),
            "end": generic.end(),
        }
    return None


def infer_unit(text: str, offset: int) -> str | None:
    tail = text[offset: offset + 36]
    match = re.match(r"\s*(people|persons|students|households|jobs|acres|tons|dollars|pages|documents|records|months|years|percent|percentage points)\b", tail, re.I)
    return match.group(1).lower() if match else None


def should_skip_number(value: str, text: str, start: int, node: dict) -> bool:
    if value.isdigit() and len(value) < 2:
        return True
    if re.fullmatch(r"(?:19|20)\d{2}", value):
        return True
    for ref in node.get("refs") or []:
        if len(ref) >= 2 and ref[0] <= start < ref[1]:
            return True
    prefix = text[max(0, start - 16):start].lower()
    if re.search(r"\b(page|p\.|section|§|usc|c\.f\.r\.)\s*\Z", prefix):
        return True
    return False


def is_strong_metric_value(value: str) -> bool:
    return bool(re.search(r"[$%]|\b(million|billion|thousand|percent)\b", value or "", re.I))


def is_action_item(text: str) -> bool:
    return bool(ACTION_START_RE.search(text or "") or RECOMMENDATION_RE.search(text or ""))


def is_recommendation_text(text: str) -> bool:
    first = first_sentence(text)
    if "?" in first:
        return False
    if not RECOMMENDATION_RE.search(first):
        return False
    return bool(re.search(r"\b(should|must|need to|needs to|recommend|increase|fund|create|adopt|require|expand|establish|invest|coordinate|evaluate)\b", first, re.I))


def infer_label(text: str, start: int) -> str | None:
    prefix = text[max(0, start - 80):start].strip(" :-,;")
    if not prefix:
        return None
    return clean_quote(prefix.split(".")[-1].strip(), 80)


def question_like_prompt(node: dict, text: str) -> str | None:
    text = clean_quote(text, 220)
    lead = node.get("lead")
    if isinstance(lead, int) and lead > 8:
        prompt = text[:lead].strip(" :")
    else:
        prompt = text.strip(" :")
    if not prompt or "?" in prompt or len(prompt) > 150:
        return None
    if QUESTION_PROMPT_RE.match(prompt):
        return prompt
    return None


def following_answer(text: str, question: str) -> str | None:
    idx = text.find(question)
    if idx == -1:
        return None
    answer = text[idx + len(question):].strip()
    return clean_quote(answer, 180) if answer else None


def sentence_containing(text: str, needle: str) -> str:
    idx = text.find(needle)
    if idx == -1:
        return clean_quote(text)
    return sentence_around(text, idx, idx + len(needle))


def clean_entity_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip(" ,;:.")


def is_entity_candidate(text: str, heading: bool = False) -> bool:
    if not text or len(text) < 4 or len(text) > 90:
        return False
    if text in ENTITY_STOPWORDS or text.upper() == text and len(text.split()) <= 3:
        return False
    words = text.split()
    if len(words) == 1:
        return words[0] in ENTITY_SUFFIXES
    if any(w.strip(".,") in ENTITY_SUFFIXES for w in words):
        return True
    return False


def entities_in_text(text: str) -> list[str]:
    found = []
    seen = set()
    for match in ENTITY_PHRASE_RE.finditer(text or ""):
        entity = clean_entity_text(match.group(0))
        if not is_entity_candidate(entity):
            continue
        if entity not in seen:
            found.append(entity)
            seen.add(entity)
    return found[:6]


def infer_entity_type(entity: str) -> str:
    lowered = entity.lower()
    if any(word in lowered for word in ("health", "clinic", "hospital", "medical")):
        return "organization"
    if any(word in lowered for word in ("foundation", "fund", "partners", "network", "coalition", "council", "center")):
        return "organization"
    if any(word in lowered for word in ("act", "law", "regulation")):
        return "law_or_policy"
    if any(word in lowered for word in ("project", "program", "initiative")):
        return "program_or_initiative"
    return "entity"


def label_values_from_container(node: dict) -> list[dict[str, str]]:
    return label_values_from_texts([n.get("text", "") for n in irwalk.leaves([node])])


def label_values_from_texts(texts: list[str]) -> list[dict[str, str]]:
    out = []
    for text in texts:
        match = LABEL_VALUE_RE.match(text)
        if match and NUMBER_RE.search(match.group("value")):
            out.append({"label": clean_quote(match.group("label"), 80), "value": clean_quote(match.group("value"), 80)})
    return out



def unique_texts(texts) -> list[str]:
    out = []
    seen = set()
    for text in texts:
        key = re.sub(r"\W+", "", (text or "").lower())[:120]
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def dedupe_stats(stats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    seen = set()
    for stat in stats:
        key = (stat.get("value"), re.sub(r"\W+", "", (stat.get("quote") or "").lower())[:120])
        if key in seen:
            continue
        seen.add(key)
        out.append(stat)
    return out

def recommendations(pattern_type: str, registry_entry: dict[str, Any]) -> list[dict[str, Any]]:
    treatments = registry_entry.get("candidate_component_treatments") or []
    if not treatments:
        return []
    return [{
        "component_type": treatments[0],
        "fit_score": 0.65,
        "reason": f"Default treatment for {pattern_type} pending human review.",
        "safety": "safe_transform",
    }]
