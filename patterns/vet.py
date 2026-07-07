"""LLM-assisted first-pass vetting for deterministic pattern candidates."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rk3.ai import complete_json, get_ai_config

from .io import LLM_REVIEWS, OUT, read_json
from .review import latest_decisions, load_review_decisions


VET_SCHEMA = {
    "type": "object",
    "properties": {
        "reviews": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pattern_id": {"type": "string"},
                    "decision": {"type": "string", "enum": ["accept", "reject", "wrong_type", "needs_more_context"]},
                    "confidence": {"type": "number"},
                    "reason": {"type": "string"},
                    "evidence_in_real_world": {"type": "boolean"},
                    "non_evidence_reasons": {"type": "array", "items": {"type": "string"}},
                    "corrected_pattern_type": {"type": ["string", "null"]},
                    "field_edits": {"type": "object"},
                },
                "required": [
                    "pattern_id",
                    "decision",
                    "confidence",
                    "reason",
                    "evidence_in_real_world",
                    "non_evidence_reasons",
                    "corrected_pattern_type",
                    "field_edits",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["reviews"],
    "additionalProperties": False,
}


SYSTEM_PROMPT = """You are a development reviewer for deterministic document-pattern candidates.

Your job is first-pass vetting, not final extraction. Apply the owner's rubric:
- Accept evidence of something real in the world that is reusable and meaningful for the document.
- Reject questions, prompts, examples, hypotheticals, URLs, footnotes/citations, methodology/admin text, publication titles, and flattened table noise.
- For statistic, impact_statement, funding_event, and metric_cluster, require a real-world claim. Rules, definitions, thresholds, section numbers, survey respondent counts, and process timing are usually not evidence.
- Use wrong_type when the source text is useful but clearly belongs to another pattern type.
- Use needs_more_context when the excerpt may be useful but the local evidence is insufficient.
- Be concise and specific; explain the rule signal that drove the decision.
"""


def vet_candidates(
    document_id: str,
    *,
    pattern_type: str | None = None,
    limit: int | None = None,
    batch_size: int = 12,
    dry_run: bool = False,
    write: bool = False,
    provider: str | None = None,
    model: str | None = None,
    skip_human_reviewed: bool = False,
) -> dict[str, Any]:
    report = read_json(OUT / f"{document_id}.json")
    candidates = select_candidates(report.get("candidates", []), pattern_type)
    if skip_human_reviewed:
        reviewed = human_reviewed_ids(document_id)
        candidates = [candidate for candidate in candidates if candidate.get("pattern_id") not in reviewed]
    if limit is not None:
        candidates = candidates[:limit]

    examples = review_examples(limit=10)
    batches = [candidates[i:i + batch_size] for i in range(0, len(candidates), batch_size)]
    config = get_ai_config()
    out = {
        "document_id": document_id,
        "candidate_count": len(candidates),
        "batch_count": len(batches),
        "provider": provider or config["provider"],
        "model": model or config["model"],
        "dry_run": dry_run,
        "reviews": [],
    }

    if dry_run:
        first_batch = batches[0] if batches else []
        out["prompt_preview"] = build_user_prompt(document_id, first_batch, examples)
        return out

    for batch in batches:
        if not batch:
            continue
        response = complete_json(
            SYSTEM_PROMPT,
            build_user_prompt(document_id, batch, examples),
            VET_SCHEMA,
            max_tokens=3500,
            provider=provider,
            model=model,
        )
        out["reviews"].extend(normalize_reviews(document_id, batch, response.get("reviews", []), out["provider"], out["model"]))

    if write and out["reviews"]:
        path = write_llm_reviews(document_id, out["reviews"])
        out["write_path"] = str(path)
    return out


def select_candidates(candidates: list[dict[str, Any]], pattern_type: str | None) -> list[dict[str, Any]]:
    rows = candidates
    if pattern_type:
        rows = [candidate for candidate in rows if candidate.get("pattern_type") == pattern_type]
    return sorted(rows, key=lambda c: ((c.get("source_refs") or [{}])[0].get("page") or 0, c.get("pattern_type") or "", c.get("pattern_id") or ""))


def human_reviewed_ids(document_id: str) -> set[str]:
    rows, _errors = load_review_decisions(document_id)
    return {str(row.get("pattern_id")) for row in latest_decisions(rows) if row.get("pattern_id")}


def review_examples(limit: int = 10) -> list[dict[str, Any]]:
    rows, _errors = load_review_decisions()
    latest = latest_decisions(rows)
    noted = [row for row in latest if row.get("notes")]
    examples = []
    for row in noted[-limit:]:
        examples.append({
            "pattern_type": row.get("pattern_type"),
            "decision": row.get("decision"),
            "notes": row.get("notes"),
        })
    return examples


def build_user_prompt(document_id: str, candidates: list[dict[str, Any]], examples: list[dict[str, Any]]) -> str:
    payload = {
        "document_id": document_id,
        "human_review_examples": examples,
        "candidates": [candidate_payload(candidate) for candidate in candidates],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def candidate_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    ref = (candidate.get("source_refs") or [{}])[0]
    return {
        "pattern_id": candidate.get("pattern_id"),
        "pattern_type": candidate.get("pattern_type"),
        "confidence": candidate.get("confidence"),
        "reason": candidate.get("reason"),
        "page": ref.get("page"),
        "quote": ref.get("quote"),
        "fields": candidate.get("fields") or {},
    }


def normalize_reviews(document_id: str, batch: list[dict[str, Any]], reviews: list[dict[str, Any]], provider: str, model: str) -> list[dict[str, Any]]:
    by_id = {candidate.get("pattern_id"): candidate for candidate in batch}
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for review in reviews:
        pattern_id = review.get("pattern_id")
        candidate = by_id.get(pattern_id)
        if not candidate:
            continue
        out.append({
            "schema": 1,
            "document_id": document_id,
            "pattern_id": pattern_id,
            "pattern_type": candidate.get("pattern_type"),
            "reviewer": "llm",
            "reviewed_at": now,
            "provider": provider,
            "model": model,
            "decision": review.get("decision"),
            "confidence": review.get("confidence"),
            "reason": review.get("reason"),
            "evidence_in_real_world": review.get("evidence_in_real_world"),
            "non_evidence_reasons": review.get("non_evidence_reasons") or [],
            "corrected_pattern_type": review.get("corrected_pattern_type"),
            "field_edits": review.get("field_edits") or {},
        })
    return out


def write_llm_reviews(document_id: str, reviews: list[dict[str, Any]]) -> Path:
    LLM_REVIEWS.mkdir(parents=True, exist_ok=True)
    path = LLM_REVIEWS / f"{document_id}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        for review in reviews:
            handle.write(json.dumps(review, sort_keys=True) + "\n")
    return path
