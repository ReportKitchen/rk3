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
    r"(?P<value>(?:[$][ ]?)?\d(?:[\d,]*\d)?(?:\.\d+)?(?:[ ]?(?:%|percent|percentage points|million|billion|thousand))?)",
    re.I,
)
MONEY_RE = re.compile(
    r"(?P<amount>\$\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:million|billion|thousand|m|b))?|\b\d[\d,]*(?:\.\d+)?\s+(?:million|billion|thousand)\s+dollars\b)",
    re.I,
)
LEGAL_REFERENCE_RE = re.compile(
    r"\b(?P<bill>(?:HB|SB|HR|H\.R\.|S\.)\s*\d+[A-Z]?)\b|"
    r"\b(?P<usc>\d+\s*U\.?S\.?C\.?\s*(?:§|Sec\.?)?\s*[\w().-]+)(?=[\s,.;)]|$)|"
    r"(?P<section>§+\s*[\w().-]+)|"
    r"\b(?P<subsection>\d{2,4}\s*(?:\([a-zA-Z0-9]+\)){1,4})\b",
    re.I,
)
FUNDING_CONTEXT_RE = re.compile(
    r"\b(fund|funded|funding|grant|grants|investment|invested|investor|loan|loans|donor|donors|capital|award|awarded|committed|raised|financing|philanthrop)\w*\b",
    re.I,
)
FUNDING_NEGATIVE_CONTEXT_RE = re.compile(r"\b(fee waiver|fees? exceed|processing additional records|fee category)\b", re.I)
DISCRETE_FUNDING_ACTION_RE = re.compile(
    r"\b(received|provided|awarded|pledged|committed|granted|funded|invested|loaned|made by|launched|announced|expand its commitment)\b",
    re.I,
)
BROAD_FUNDING_SUMMARY_RE = re.compile(
    r"\b(total|known funding|average grant size|average amount of annual foundation funding|capital backlog|economic impact|funding went to|funding to projects|funding channelled|level of funding|created over|generated over|invested nearly|foundation funding was invested|grant funding awarded|grant success rate|median amount|annual expenses|annual grantmaking|top-funded|outliers)\b",
    re.I,
)
IMPACT_STATEMENT_RE = re.compile(
    r"\b(created|generated|helped|served|reached|touched|built|produced|preserved|provided|invested|awarded|funded|reduced|increased|improved|needed|needs|need|backlog|impact)\b",
    re.I,
)
PURPOSE_STATEMENT_RE = re.compile(
    r"\b(the need to|urgent|urgency|why\b.+\bmatters|problem\b.+\bsolve|exists to|mission is to|purpose is to)\b",
    re.I,
)
RESOURCE_HINT_RE = re.compile(
    r"\b(programs?|resources?|guides?|toolkits?|surveys?|reports?|databases?|datasets?|index|indices|initiative|initiatives|project|projects|fund|funds|grant|grants|academy|challenge)\b",
    re.I,
)
RESOURCE_PHRASE_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9&.'’-]+|[A-Z]{2,})(?:\s+(?:[A-Z][A-Za-z0-9&.'’-]+|of|and|for|the|to|[A-Z]{2,})){0,8}\s+(?:Programs?|Resources?|Guides?|Toolkits?|Surveys?|Reports?|Databases?|Datasets?|Index|Initiative|Initiatives|Project|Projects|Fund|Funds|Grant|Grants|Academy|Challenge)\b"
)
CALLOUT_LABELS = {
    "in their own words",
    "digging deeper",
    "policy in action",
    "case study",
    "stories of impact",
    "spotlight",
    "learn more",
}
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
DEFINITION_TERM_PREFIX_RE = re.compile(r"^(?:indicator|term|definition)\s*:\s*", re.I)
DEFINITION_TERM_QUALIFIER_RE = re.compile(r"\s+(?:typically|generally|usually|often)$", re.I)
DEFINITION_PRONOUN_TERMS = {"it", "this", "that", "these", "those", "which", "who", "what", "there"}
DEFINITION_GENERIC_TERMS = {
    "approach", "concept", "method", "process", "statistical technique", "technique",
}
QUESTION_PROMPT_RE = re.compile(r"^(what|who|when|where|why|how|which)\b.{8,140}$", re.I)
RECOMMENDATION_RE = re.compile(r"\b(should|must|need to|needs to|recommend|increase|fund|create|adopt|require|expand|establish|invest|coordinate|evaluate)\b", re.I)
KEY_FINDING_RE = re.compile(r"\b(key finding|finding|we find|this shows|this demonstrates|evidence suggests)\b", re.I)
ACTION_START_RE = re.compile(r"^\s*(partner|connect|collaborate|hold|develop|enlist|increase|fund|create|adopt|require|expand|establish|invest|coordinate|evaluate|seek|seeking|challenge|challenging|negotiate|negotiating|identify|make sure)\b", re.I)
ROLE_HINT_RE = re.compile(r"\b(ceo|director|officer|president|founder|manager|chair|principal|partner|professor|secretary|minister|attorney|counsel|lead|head|vp|vice president)\b", re.I)
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
        if is_citation_like_text(text):
            continue
        if is_chart_or_methodology_text(text):
            continue
        evidence_leaf = is_evidence_bearing_text(text, node)
        legal_spans: list[tuple[int, int]] = []
        money_spans: list[tuple[int, int]] = []
        date_spans = [match.span() for match in DATE_RE.finditer(text)]

        for match in LEGAL_REFERENCE_RE.finditer(text):
            reference = clean_legal_reference(match.group(0))
            if not reference or should_skip_legal_reference(reference, text):
                continue
            legal_spans.append(match.span())
            add(
                "legal_reference",
                node,
                {
                    "reference_text": reference,
                    "reference_type": infer_legal_reference_type(reference),
                    "context": sentence_around(text, match.start(), match.end()),
                },
                0.82,
                "Legal citation, bill number, or statutory subsection.",
                sentence_around(text, match.start(), match.end()),
            )

        for match in MONEY_RE.finditer(text):
            amount = clean_money_amount(match.group("amount"))
            quote = sentence_around(text, match.start(), match.end())
            if not evidence_leaf or not is_evidence_bearing_text(quote, node):
                continue
            if not amount or not is_funding_context(quote):
                continue
            money_spans.append(match.span())
            if not is_discrete_funding_event(quote):
                add(
                    "impact_statement",
                    node,
                    {
                        "statement_text": quote,
                        "impact_type": infer_impact_type(quote),
                        "actor": infer_impact_actor(text, match.start()),
                        "value": amount,
                        "time_period": first_date_value(quote),
                        "beneficiaries": infer_impact_beneficiaries(quote),
                    },
                    0.68,
                    "Funding-like amount in aggregate impact, need, backlog, or summary context.",
                    quote,
                )
                continue
            parties = infer_funding_parties(quote, amount)
            fallback_funder = None if parties.get("program") else infer_funder(text, match.start())
            fields = {
                "amount": amount,
                "funder": parties.get("funder") or fallback_funder,
                "recipient": parties.get("recipient") or infer_recipient(text, match.end()),
                "program": parties.get("program"),
                "purpose": infer_funding_purpose(quote),
                "time_period": first_date_value(quote),
                "relationship_edges": [],
            }
            add(
                "funding_event",
                node,
                fields,
                0.76,
                "Currency amount in funding, grant, investment, donor, or capital context.",
                quote,
            )
            if fields["funder"] and fields["recipient"]:
                add(
                    "entity_relationship",
                    node,
                    {
                        "subject": fields["funder"],
                        "predicate": "funds",
                        "object": fields["recipient"],
                        "subject_type": infer_entity_type(fields["funder"]),
                        "object_type": infer_entity_type(fields["recipient"]),
                        "confidence_reason": "currency amount appears in funding context with inferred parties",
                    },
                    0.62,
                    "Funding context links inferred funder and recipient.",
                    quote,
                )

        purpose = find_purpose_statement(text) if evidence_leaf else None
        if purpose:
            add(
                "purpose_statement",
                node,
                purpose,
                0.66,
                "Problem-framing statement explaining why work is needed.",
                purpose["statement_text"],
            )

        impact = None if purpose or not evidence_leaf or (money_spans and is_funding_context(text)) else find_impact_statement(text)
        if impact:
            add(
                "impact_statement",
                node,
                impact,
                0.64,
                "Outcome, accomplishment, need, or impact language with measurable claim.",
                impact["statement_text"],
            )

        resource = find_resource(text)
        if resource:
            add(
                "resource",
                node,
                resource,
                0.68,
                "Named program, report, survey, guide, fund, or reusable resource.",
                resource["description"] or resource["resource_name"],
            )

        for match in NUMBER_RE.finditer(text):
            value = match.group("value").strip()
            if overlaps(match.span(), legal_spans) or overlaps(match.span(), money_spans) or overlaps(match.span(), date_spans):
                continue
            quote = sentence_around(text, match.start(), match.end())
            if not evidence_leaf or not is_evidence_bearing_text(quote, node):
                continue
            if should_skip_number(value, text, match.start(), node):
                continue
            unit = infer_unit(text, match.end())
            label = infer_label(text, match.start())
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
                quote_text = match.group("quote").strip()
                if should_skip_quote_candidate(quote_text, text):
                    continue
                add(
                    "quotation",
                    node,
                    {"quote_text": quote_text, "speaker_name": None},
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
            question = match.group("question").strip()
            if should_skip_question_candidate(question, text):
                continue
            found_question = True
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
        if is_callout_label(text):
            add(
                "callout_label",
                node,
                {"label_text": text, "module_type": infer_callout_label_type(text), "sample_content": None},
                0.72,
                "Short editorial module/callout label.",
                text,
            )
        resource = find_resource(text)
        if resource:
            add(
                "resource",
                node,
                resource,
                0.7,
                "Heading names a reusable resource or program.",
                text,
            )
        if is_entity_candidate(text, heading=True) and not is_resource_only_name(text):
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
        if is_citation_like_text(text) or is_chart_or_methodology_text(text):
            continue
        for entity in entities_in_text(text):
            if is_resource_only_name(entity):
                continue
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
        if len(usable) >= 2:
            basis = strong if len(strong) >= 2 else usable
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
        quote_payload = quote_payload_from_aside(node)
        add(
            "callout",
            node,
            {"callout_text": clean_quote(text), "callout_type": "quote" if node.get("quote") else "sidebar"},
            0.82 if node.get("quote") else 0.66,
            "IR aside container.",
            text,
        )
        if node.get("quote"):
            quote_fields = {
                "quote_text": quote_payload["quote_text"],
                "speaker_name": quote_payload.get("speaker_name"),
                "speaker_title": quote_payload.get("speaker_title"),
                "speaker_affiliation": quote_payload.get("speaker_affiliation"),
            }
            add(
                "quotation",
                node,
                quote_fields,
                0.84 if quote_payload.get("speaker_name") else 0.76,
                "IR aside marked as quote with parsed attribution." if quote_payload.get("speaker_name") else "IR aside marked as quote.",
                quote_payload["quote_text"],
            )
            if quote_payload.get("speaker_name"):
                add(
                    "named_entity",
                    node,
                    {
                        "entity_text": quote_payload["speaker_name"],
                        "entity_type": "person",
                        "source": "quote_attribution",
                    },
                    0.82,
                    "Speaker name parsed from quote attribution.",
                    quote_payload.get("attribution_text") or text,
                )
            if quote_payload.get("speaker_affiliation"):
                add(
                    "named_entity",
                    node,
                    {
                        "entity_text": quote_payload["speaker_affiliation"],
                        "entity_type": infer_entity_type(quote_payload["speaker_affiliation"]),
                        "source": "quote_attribution",
                    },
                    0.78,
                    "Speaker affiliation parsed from quote attribution.",
                    quote_payload.get("attribution_text") or text,
                )
            if quote_payload.get("speaker_name") and quote_payload.get("speaker_affiliation"):
                add(
                    "entity_relationship",
                    node,
                    {
                        "subject": quote_payload["speaker_name"],
                        "predicate": "affiliated_with",
                        "object": quote_payload["speaker_affiliation"],
                        "subject_type": "person",
                        "object_type": infer_entity_type(quote_payload["speaker_affiliation"]),
                        "confidence_reason": "quote attribution supplies person/title/organization",
                    },
                    0.78,
                    "Quote attribution links speaker to organization.",
                    quote_payload.get("attribution_text") or text,
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
        question_items = [t for t in item_texts if "?" in t and not should_skip_question_candidate(t, t)]
        question_count = len(question_items)
        action_count = sum(1 for t in item_texts if is_action_item(t))
        if len(item_texts) >= 2 and question_count >= max(2, len(item_texts) // 2):
            add(
                "question_list",
                node,
                {"questions": question_items[:20]},
                0.84,
                "Multiple question-like items in an IR list.",
                "\n".join(question_items),
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
        term = normalize_definition_term(which.group("term"))
        if not is_definition_term(term):
            return None
        definition = which.group("definition").strip()
        if should_skip_definition_text(definition):
            return None
        return {
            "term": term,
            "definition": definition,
            "start": which.start(),
            "end": which.end(),
        }
    generic = DEFINITION_RE.search(text or "")
    if generic:
        term = normalize_definition_term(generic.group("term"))
        if not is_definition_term(term):
            return None
        definition = generic.group("definition").strip()
        if should_skip_definition_text(definition):
            return None
        return {
            "term": term,
            "definition": definition,
            "start": generic.start(),
            "end": generic.end(),
        }
    return None


def normalize_definition_term(term: str) -> str:
    term = clean_entity_text((term or "").strip(" \"'“”‘’"))
    term = DEFINITION_TERM_PREFIX_RE.sub("", term)
    term = re.sub(r"^(?:a|an|the)\s+", "", term, flags=re.I)
    term = DEFINITION_TERM_QUALIFIER_RE.sub("", term)
    return clean_entity_text(term)


def is_definition_term(term: str) -> bool:
    if not term:
        return False
    lowered = term.lower()
    words = term.split()
    if lowered in DEFINITION_PRONOUN_TERMS or lowered in DEFINITION_GENERIC_TERMS:
        return False
    if words and words[0].lower() in DEFINITION_PRONOUN_TERMS:
        return False
    if len(words) > 8:
        return False
    is_all_caps_term = term.upper() == term and any(ch.isalpha() for ch in term)
    has_upper = any(ch.isupper() for ch in term)
    if not has_upper and len(words) > 3:
        return False
    if not has_upper and re.search(r"\b(is|are|was|were|does|do|did|has|have|had|not|in|as|by|to)\b", lowered):
        return False
    if not is_all_caps_term and re.search(r"\b(is|are|was|were|does|do|did|has|have|had|represent|represents)\b", lowered):
        return False
    return True


def should_skip_definition_text(definition: str) -> bool:
    lowered = (definition or "").strip().lower()
    if lowered.startswith(("that ", "to both ", "we ", "they ", "from ")):
        return True
    return False


def infer_unit(text: str, offset: int) -> str | None:
    tail = text[offset: offset + 36]
    match = re.match(r"\s*(people|persons|students|households|jobs|acres|tons|dollars|pages|documents|records|months|years|percent|percentage points)\b", tail, re.I)
    return match.group(1).lower() if match else None


def should_skip_number(value: str, text: str, start: int, node: dict) -> bool:
    normalized_value = (value or "").strip(" ,.;:")
    end = start + len(value or "")
    if value.isdigit() and len(value) < 2:
        return True
    if is_money_value(value):
        return True
    if re.fullmatch(r"(?:19|20)\d{2}", normalized_value):
        return True
    if re.fullmatch(r"(?:19|20)\d{3}", normalized_value):
        return True
    if is_embedded_number_token(text, start, end):
        return True
    if month_day_fragment_near(text, start):
        return True
    if legal_reference_near(text, start):
        return True
    for ref in node.get("refs") or []:
        if len(ref) >= 2 and ref[0] <= start < ref[1]:
            return True
    prefix = text[max(0, start - 16):start].lower()
    suffix = text[end:end + 16].lower()
    if re.search(r"\b(page|p\.|section|§|usc|c\.f\.r\.)\s*\Z", prefix):
        return True
    if re.match(r"\s*(?:u\.?s\.?c\.?|c\.?f\.?r\.?|usc|cfr)\b", suffix):
        return True
    return False


def is_embedded_number_token(text: str, start: int, end: int) -> bool:
    text = text or ""
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    if (before and before.isalpha()) or (after and after.isalpha()):
        return True
    if (before and before in "-–‑") or (after and after in "-–‑"):
        return True
    prefix = text[max(0, start - 12):start]
    suffix = text[end:end + 12]
    if re.search(r"[A-Z]{2,}[-–‑]?$", prefix) or re.match(r"[-–‑]?[A-Z]{2,}", suffix):
        return True
    return False


def month_day_fragment_near(text: str, start: int) -> bool:
    prefix = text[max(0, start - 16):start]
    return bool(
        re.search(
            r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
            r"\s*$",
            prefix,
            re.I,
        )
    )


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
    if text.endswith(":"):
        return None
    lead = node.get("lead")
    if isinstance(lead, int) and lead > 8:
        prompt = text[:lead].strip(" :")
    else:
        prompt = text.strip(" :")
    if not prompt or "?" in prompt or len(prompt) > 150:
        return None
    if prompt.endswith("."):
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


def should_skip_question_candidate(question: str, text: str) -> bool:
    if is_chart_or_methodology_text(question):
        return True
    lowered_question = (question or "").lower()
    if lowered_question.startswith(("a bigger,", "a narrow,", "shouldn’t we", "shouldn't we")):
        return True
    lowered = (text or "").lower()
    if lowered.startswith(("figure ", "fig. ", "chart ", "table ")):
        return True
    if "ask yourself" in lowered or "think ahead of time" in lowered or "what you plan to do" in lowered:
        return True
    if lowered_question.startswith("will your request have an advocacy or media impact"):
        return True
    idx = (text or "").find(question)
    after = (text or "")[idx + len(question): idx + len(question) + 8] if idx != -1 else ""
    if after.strip().startswith(("”", '"')):
        return True
    return False


def should_skip_quote_candidate(quote_text: str, full_text: str) -> bool:
    lowered_full = (full_text or "").lower()
    lowered_quote = (quote_text or "").lower()
    if "example:" in lowered_full or lowered_full.strip().startswith(("example", "sample")):
        return True
    if re.search(r"\b(this is a request under|please provide|requester certifies|may i|dear\b)", lowered_quote):
        return True
    if len((quote_text or "").split()) <= 4 and is_resource_name(quote_text):
        return True
    return False


def is_evidence_bearing_text(text: str, node: dict | None = None) -> bool:
    text = clean_quote(text, 320)
    if not text:
        return False
    if node and node.get("type") == "heading":
        return False
    if is_citation_like_text(text) or is_url_like_text(text):
        return False
    if is_chart_or_methodology_text(text) or is_survey_admin_text(text):
        return False
    if is_question_evidence_text(text):
        return False
    if is_example_or_hypothetical_text(text):
        return False
    if is_definition_rule_or_threshold_text(text):
        return False
    if is_publication_title_like_text(text):
        return False
    return True


def is_url_like_text(text: str) -> bool:
    return bool(re.search(r"\b(?:https?://|www\.|[A-Za-z0-9.-]+\.(?:org|com|edu|gov|net)(?:/|\b))", text or "", re.I))


def is_question_evidence_text(text: str) -> bool:
    cleaned = (text or "").strip()
    lowered = cleaned.lower()
    if "?" in cleaned:
        return True
    return bool(
        lowered.startswith(("ask yourself", "before you start", "consider whether"))
        or re.search(r"\b(ask yourself|questions to ask|guiding questions|discussion questions)\b", lowered)
    )


def is_example_or_hypothetical_text(text: str) -> bool:
    lowered = (text or "").strip().lower()
    return bool(
        lowered.startswith(("for example", "example:", "sample ", "hypothetical"))
        or re.search(r"\b(example metric|for instance|e\.g\.|hypothetical|scenario|suppose|imagine)\b", lowered)
    )


def is_definition_rule_or_threshold_text(text: str) -> bool:
    lowered = (text or "").strip().lower()
    return bool(
        re.search(r"\b(is defined as|are defined as|defined as|definition:|refers to|means)\b", lowered)
        or re.search(r"\b(rule|threshold|limit|minimum|maximum|requirement|requires|required|must be|no more than|at least)\b", lowered)
    )


def is_survey_admin_text(text: str) -> bool:
    lowered = (text or "").strip().lower()
    return bool(
        re.search(r"\b(survey respondents?|respondents? to (?:the|our) survey|survey sample|sample size|n=|demographic makeup)\b", lowered)
        or re.search(r"\b(asked .* questions|closed- and open-ended questions|open-ended questions|responded to (?:the|our) survey)\b", lowered)
    )


def is_publication_title_like_text(text: str) -> bool:
    cleaned = clean_entity_text(text)
    if not cleaned or len(cleaned) > 120:
        return False
    lowered = cleaned.lower()
    if re.search(r"\b(book|publication|article|chapter|report|guide|toolkit|housing 101|opportunity 360)\b", lowered):
        if not re.search(r"\b(created|generated|served|reached|increased|decreased|funded|awarded|received|pledged|provided)\b", lowered):
            return True
    if len(cleaned.split()) <= 8 and cleaned.istitle() and not re.search(r"[.!?]", cleaned):
        return bool(RESOURCE_HINT_RE.search(cleaned))
    return False


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
    if any(word in lowered for word in ("authority", "authorities", "corporation", "foundation", "fund", "partners", "network", "coalition", "council", "center")):
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


def overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(start < other_end and end > other_start for other_start, other_end in spans)


def is_money_value(value: str) -> bool:
    return bool(MONEY_RE.fullmatch((value or "").strip()))


def clean_money_amount(amount: str) -> str:
    return re.sub(r"\s+", " ", amount or "").strip()


def is_funding_context(text: str) -> bool:
    if FUNDING_NEGATIVE_CONTEXT_RE.search(text or ""):
        return False
    return bool(FUNDING_CONTEXT_RE.search(text or ""))


def is_discrete_funding_event(text: str) -> bool:
    text = text or ""
    if BROAD_FUNDING_SUMMARY_RE.search(text):
        return False
    if re.search(r"\b(should|recommend|raise the guarantee cap|annually|increased investment of|increase investment of)\b", text, re.I):
        return False
    return bool(DISCRETE_FUNDING_ACTION_RE.search(text))


def legal_reference_near(text: str, start: int) -> bool:
    window_start = max(0, start - 24)
    window_end = min(len(text), start + 48)
    return bool(LEGAL_REFERENCE_RE.search(text[window_start:window_end]))


def infer_legal_reference_type(reference: str) -> str:
    ref = reference.strip()
    lowered = ref.lower()
    if re.match(r"^(hb|sb|hr|h\.r\.|s\.)\s*\d+", lowered):
        return "bill_number"
    if "usc" in lowered or "u.s.c" in lowered:
        return "statute"
    if ref.startswith("§"):
        return "section"
    if re.match(r"^\d{2,4}\s*(?:\([a-zA-Z0-9]+\)){1,4}$", ref):
        return "legal_subsection"
    return "legal_reference"


def clean_legal_reference(reference: str) -> str:
    ref = (reference or "").strip().rstrip(".,;")
    while ref.endswith(")") and ref.count(")") > ref.count("("):
        ref = ref[:-1].rstrip()
    return ref


def should_skip_legal_reference(reference: str, text: str) -> bool:
    if re.fullmatch(r"501\s*\(?c\)?\s*3?", reference or "", re.I):
        return True
    if "501(c)" in (text or "").lower():
        return True
    return False


def first_date_value(text: str) -> str | None:
    match = DATE_RE.search(text or "")
    return match.group(0) if match else None


def infer_funder(text: str, amount_start: int) -> str | None:
    prefix = text[max(0, amount_start - 140):amount_start]
    candidates = entities_in_text(prefix)
    return candidates[-1] if candidates else None


def infer_funding_parties(quote: str, amount: str) -> dict[str, str | None]:
    parties: dict[str, str | None] = {"funder": None, "program": None, "recipient": None}
    if not quote or not amount:
        return parties

    escaped_amount = re.escape(amount)
    program_match = re.search(rf"\blaunched\s+(?P<program>.+?),\s+a\s+{escaped_amount}\s+program\b", quote, re.I)
    if program_match:
        program_candidates = entities_in_text(program_match.group("program"))
        parties["program"] = program_candidates[-1] if program_candidates else clean_entity_text(program_match.group("program"))

    received = re.search(
        rf"(?P<recipient>.+?)\s+received\s+{escaped_amount}.*?\bfrom\s+(?P<funder>.+?)(?:[.;,]|$)",
        quote,
        re.I,
    )
    if received:
        recipient_candidates = entities_in_text(received.group("recipient"))
        funder_candidates = entities_in_text(received.group("funder"))
        parties["recipient"] = recipient_candidates[-1] if recipient_candidates else None
        parties["funder"] = funder_candidates[0] if funder_candidates else clean_entity_text(received.group("funder"))
        return parties

    by_match = re.search(r"\b(?:pledge|grant|investment|award).*?\b(?:made|provided|funded|awarded)\s+by\s+(?P<funder>.+?)(?:[.;,]|$)", quote, re.I)
    if by_match:
        funder_candidates = entities_in_text(by_match.group("funder"))
        parties["funder"] = funder_candidates[0] if funder_candidates else clean_entity_text(by_match.group("funder"))

    to_match = re.search(rf"{escaped_amount}.*?\b(?:to|for|supporting)\s+(?P<recipient>.+?)(?:[.;,]|$)", quote, re.I)
    if to_match:
        recipient_candidates = entities_in_text(to_match.group("recipient"))
        parties["recipient"] = recipient_candidates[0] if recipient_candidates else None
    return parties


def infer_recipient(text: str, amount_end: int) -> str | None:
    tail = text[amount_end:amount_end + 160]
    match = re.search(r"\b(?:to|for|in|into|supporting)\s+(.+?)(?:[.;,]|$)", tail, re.I)
    if not match:
        return None
    candidates = entities_in_text(match.group(1))
    return candidates[0] if candidates else None


def infer_funding_purpose(quote: str) -> str | None:
    match = re.search(r"\b(?:to|for|supporting|toward)\s+(.+?)(?:[.;]|$)", quote or "", re.I)
    return clean_quote(match.group(1), 140) if match else None


def find_purpose_statement(text: str) -> dict[str, Any] | None:
    quote = first_sentence(text)
    if not quote or len(quote) < 40:
        return None
    if is_chart_or_methodology_text(quote) or is_citation_like_text(quote):
        return None
    if not PURPOSE_STATEMENT_RE.search(quote):
        return None
    if re.search(r"\b(should|recommend|must)\b", quote, re.I):
        return None
    return {
        "statement_text": quote,
        "problem": infer_purpose_problem(quote),
        "audience": infer_impact_beneficiaries(quote),
        "stakes": infer_purpose_stakes(quote),
    }


def infer_purpose_problem(text: str) -> str | None:
    match = re.search(r"\b(?:need to|urgent(?:ly)?(?: need)? to|problem(?: is| of)?|solve)\s+(.+?)(?:[.;]|$)", text or "", re.I)
    return clean_quote(match.group(1), 140) if match else None


def infer_purpose_stakes(text: str) -> str | None:
    match = re.search(r"\b(?:because|so that|in order to)\s+(.+?)(?:[.;]|$)", text or "", re.I)
    return clean_quote(match.group(1), 140) if match else None


def find_impact_statement(text: str) -> dict[str, Any] | None:
    quote = first_sentence(text)
    if not quote or len(quote) < 30:
        return None
    if is_chart_or_methodology_text(quote) or is_definition_like_impact(quote):
        return None
    if not IMPACT_STATEMENT_RE.search(quote):
        return None
    has_value = bool(NUMBER_RE.search(quote) or MONEY_RE.search(quote) or re.search(r"\b(millions?|billions?|thousands?)\b", quote, re.I))
    if not has_value and "," in quote and ROLE_HINT_RE.search(quote):
        return None
    if not has_value and not re.search(r"\b(backlog|need|needs|impact)\b", quote, re.I):
        return None
    return {
        "statement_text": quote,
        "impact_type": infer_impact_type(quote),
        "actor": infer_impact_actor(text, 0),
        "value": first_impact_value(quote),
        "time_period": first_date_value(quote),
        "beneficiaries": infer_impact_beneficiaries(quote),
        "scope": None,
    }


def infer_impact_type(text: str) -> str:
    lowered = (text or "").lower()
    if any(word in lowered for word in ("backlog", "need", "needed", "needs")):
        return "need"
    if any(word in lowered for word in ("economic impact", "touched", "served", "reached", "helped", "created", "generated")):
        return "accomplishment"
    if any(word in lowered for word in ("known funding", "average grant", "funding went", "foundation funding")):
        return "funding_summary"
    return "impact"


def first_impact_value(text: str) -> str | None:
    money = MONEY_RE.search(text or "")
    if money:
        return clean_money_amount(money.group("amount"))
    number = NUMBER_RE.search(text or "")
    if number:
        return number.group("value").strip()
    word_number = re.search(r"\b(millions?|billions?|thousands?)\b", text or "", re.I)
    return word_number.group(0) if word_number else None


def infer_impact_actor(text: str, offset: int) -> str | None:
    prefix = text[max(0, offset - 160): offset + 160]
    candidates = entities_in_text(prefix)
    return candidates[0] if candidates else None


def infer_impact_beneficiaries(text: str) -> str | None:
    match = re.search(r"\b(?:for|to|among|serving|served|reached|touched|helped)\s+(.+?)(?:[.;,]|$)", text or "", re.I)
    return clean_quote(match.group(1), 100) if match else None


def find_resource(text: str) -> dict[str, Any] | None:
    text = clean_quote(text, 260)
    if not text or len(text) < 5:
        return None
    if is_citation_like_text(text):
        return None
    label_match = LABEL_VALUE_RE.match(text)
    if label_match and RESOURCE_HINT_RE.search(label_match.group("label")):
        name = clean_entity_text(label_match.group("label"))
        if not is_plausible_resource_name(name):
            return None
        return {
            "resource_name": name,
            "resource_type": infer_resource_type(name),
            "sponsor": None,
            "description": clean_quote(text, 220),
        }
    phrase = RESOURCE_PHRASE_RE.search(text)
    if phrase:
        name = clean_entity_text(phrase.group(0))
        if name and name.lower() not in CALLOUT_LABELS and is_plausible_resource_name(name):
            return {
                "resource_name": name,
                "resource_type": infer_resource_type(name),
                "sponsor": None,
                "description": sentence_containing(text, name),
            }
    return None


def is_resource_name(text: str) -> bool:
    return bool(RESOURCE_HINT_RE.search(text or ""))


def is_resource_only_name(text: str) -> bool:
    return bool(re.search(r"\b(survey|report|guide|toolkit|database|dataset|index|indices)\b", text or "", re.I))


def infer_resource_type(name: str) -> str:
    lowered = (name or "").lower()
    for key, value in (
        ("survey", "survey"),
        ("report", "report"),
        ("guide", "guide"),
        ("toolkit", "toolkit"),
        ("database", "database"),
        ("dataset", "dataset"),
        ("program", "program"),
        ("fund", "fund"),
        ("grant", "grant_program"),
        ("initiative", "initiative"),
        ("project", "project"),
        ("academy", "academy"),
        ("challenge", "challenge"),
    ):
        if key in lowered:
            return value
    return "resource"


def is_plausible_resource_name(name: str) -> bool:
    if not name or len(name) < 5 or len(name) > 120:
        return False
    lowered = name.lower()
    if lowered.startswith(("this ", "these ", "that ", "about ", "co-director", "senior director", "director ")):
        return False
    if re.search(r"\b(director|chief executive|president|founder|author|authors?)\b", lowered):
        return False
    if not RESOURCE_HINT_RE.search(name):
        return False
    return True


def is_chart_or_methodology_text(text: str) -> bool:
    lowered = (text or "").strip().lower()
    return bool(
        lowered.startswith(("figure ", "fig. ", "chart ", "table ", "base:"))
        or re.search(r"\b(n=\d|sample size|respondents in the survey|demographic makeup|methodolog(?:y|ies))\b", lowered)
    )


def is_definition_like_impact(text: str) -> bool:
    return bool(re.search(r"\b(impact refers to|impact is|is defined as|means)\b", text or "", re.I))


def is_citation_like_text(text: str) -> bool:
    text = text or ""
    lowered = text.lower()
    if re.search(r"\b(et al\.|accessed|retrieved|doi|https?://|journal|quarterly|press|vol\.|no\.)\b", lowered):
        return True
    if re.search(r"\b\d+\(\d+\),\s*\d+[-–]\d+\b", text):
        return True
    if re.search(r"\bp\.\s*\d+\b", lowered) and "/" in text:
        return True
    return False


def is_callout_label(text: str) -> bool:
    cleaned = clean_entity_text(text).lower()
    if cleaned in CALLOUT_LABELS:
        return True
    return bool(len(cleaned.split()) <= 5 and re.search(r"\b(words|deeper|spotlight|action|impact)\b", cleaned))


def infer_callout_label_type(text: str) -> str:
    cleaned = (text or "").lower()
    if "own words" in cleaned:
        return "first_person_quote"
    if "policy" in cleaned:
        return "policy_example"
    if "impact" in cleaned:
        return "impact_story"
    return "editorial_module"


def quote_payload_from_aside(node: dict) -> dict[str, str | None]:
    leaves = [leaf for leaf in irwalk.leaves([node]) if leaf.get("text")]
    quote_leaf = next((leaf for leaf in leaves if leaf.get("quoteOpen")), None)
    if quote_leaf is None and leaves:
        quote_leaf = leaves[0]
    quote_text = clean_quote(quote_leaf.get("text") if quote_leaf else irwalk.subtree_text(node))

    attribution_text = None
    role_text = None
    if quote_leaf is not None:
        quote_index = leaves.index(quote_leaf)
        for i, leaf in enumerate(leaves[quote_index + 1:], start=quote_index + 1):
            candidate = clean_quote(leaf.get("text") or "", 180)
            if starts_new_quote(candidate):
                break
            if looks_like_speaker_line(candidate):
                attribution_text = candidate
                if should_scan_role_text(candidate):
                    for role_leaf in leaves[i + 1:]:
                        role_candidate = clean_quote(role_leaf.get("text") or "", 180)
                        if starts_new_quote(role_candidate):
                            break
                        if looks_like_role_line(role_candidate):
                            role_text = role_candidate
                            break
                break

    attribution = parse_attribution(attribution_text or "", role_text)
    return {
        "quote_text": quote_text,
        "attribution_text": " ".join(part for part in (attribution_text, role_text) if part),
        "speaker_name": attribution.get("speaker_name"),
        "speaker_title": attribution.get("speaker_title"),
        "speaker_affiliation": attribution.get("speaker_affiliation"),
    }


def starts_new_quote(text: str) -> bool:
    return bool((text or "").lstrip().startswith(("“", '"')) or len(text or "") > 220)


def looks_like_speaker_line(text: str) -> bool:
    if not text or len(text) > 180:
        return False
    if "," in text and looks_like_person_name(text.split(",", 1)[0]):
        return True
    return looks_like_person_name(text) and not role_only_text(text)


def looks_like_role_line(text: str) -> bool:
    if not text or len(text) > 160:
        return False
    return bool(ROLE_HINT_RE.search(text) or ("," in text and entities_in_text(text)))


def should_scan_role_text(text: str) -> bool:
    if "," not in text:
        return True
    parts = [part.strip() for part in text.split(",") if part.strip()]
    return bool(len(parts) >= 2 and all(is_credential(part) for part in parts[1:]))


def parse_attribution(text: str, role_text: str | None = None) -> dict[str, str | None]:
    if not text:
        return {"speaker_name": None, "speaker_title": None, "speaker_affiliation": None}
    parts = [part.strip() for part in text.split(",") if part.strip()]
    speaker_name = parts[0] if parts and looks_like_person_name(parts[0]) else None
    speaker_title = None
    speaker_affiliation = None

    if role_text:
        role_parts = [part.strip() for part in role_text.split(",") if part.strip()]
        if len(role_parts) >= 2:
            speaker_title = clean_quote(role_parts[0], 90)
            speaker_affiliation = clean_entity_text(", ".join(role_parts[1:]))
        elif role_parts:
            of_match = re.search(r"\b(?P<title>.+?)\s+(?:of|at|for|with)\s+(?P<org>.+)$", role_parts[0], re.I)
            if of_match:
                speaker_title = clean_quote(of_match.group("title"), 90)
                speaker_affiliation = clean_entity_text(of_match.group("org"))
            elif ROLE_HINT_RE.search(role_parts[0]):
                speaker_title = clean_quote(role_parts[0], 90)
            else:
                speaker_affiliation = clean_entity_text(role_parts[0])
    elif len(parts) >= 2:
        remaining = ", ".join(parts[1:])
        of_match = re.search(r"\b(?P<title>.+?)\s+(?:of|at|for|with)\s+(?P<org>.+)$", remaining, re.I)
        if of_match:
            speaker_title = clean_quote(of_match.group("title"), 90)
            speaker_affiliation = clean_entity_text(of_match.group("org"))
        elif len(parts) >= 3:
            speaker_title = clean_quote(parts[1], 90)
            speaker_affiliation = clean_entity_text(", ".join(parts[2:]))
        elif ROLE_HINT_RE.search(parts[1]):
            speaker_title = clean_quote(parts[1], 90)
        else:
            speaker_affiliation = clean_entity_text(parts[1])

    if speaker_affiliation:
        speaker_affiliation = speaker_affiliation.strip(" .")
    return {
        "speaker_name": speaker_name,
        "speaker_title": speaker_title,
        "speaker_affiliation": speaker_affiliation or None,
    }


def looks_like_person_name(text: str) -> bool:
    words = [word.strip(".") for word in re.split(r"\s+", text or "") if word.strip()]
    if len(words) < 2 or len(words) > 4:
        return False
    if role_only_text(text):
        return False
    return all(re.match(r"^[A-Z][A-Za-z.'’-]+$", word) for word in words)


def is_credential(text: str) -> bool:
    return bool(re.fullmatch(r"(?:[A-Z]\.){1,4}", (text or "").strip()))


def role_only_text(text: str) -> bool:
    words = [word.strip(".,").lower() for word in re.split(r"\s+", text or "") if word.strip()]
    if not words:
        return False
    role_words = {"secretary", "director", "president", "ceo", "officer", "manager", "chair", "minister", "attorney", "counsel"}
    modifiers = {"former", "interim", "deputy", "executive", "hud"}
    return any(word in role_words for word in words) and all(word in role_words or word in modifiers for word in words)



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
