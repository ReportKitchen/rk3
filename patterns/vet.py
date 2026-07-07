"""LLM-assisted first-pass vetting for deterministic pattern candidates."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
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


def load_llm_reviews(document_id: str | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    paths = sorted(LLM_REVIEWS.glob("*.jsonl"))
    if document_id:
        paths = [path for path in paths if path.stem == document_id]

    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append({"file": str(path), "line": line_number, "error": str(exc)})
                continue
            row.setdefault("document_id", path.stem)
            row["_file"] = str(path)
            row["_line"] = line_number
            rows.append(row)
    return rows, errors


def summarize_llm_reviews(document_id: str | None = None) -> dict[str, Any]:
    rows, errors = load_llm_reviews(document_id)
    latest = latest_decisions(rows)
    return {
        "document_id": document_id,
        "files_read": sorted({row["_file"] for row in rows}),
        "row_count": len(rows),
        "latest_pattern_count": len(latest),
        "parse_errors": errors,
        "latest_decisions": count_llm_rows(latest),
        "non_evidence_reasons": count_non_evidence_reasons(latest),
        "recent_reviews": recent_llm_reviews(latest),
    }


def count_llm_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_type_decision = Counter((row.get("pattern_type") or "unknown", row.get("decision") or "unknown") for row in rows)
    by_type: dict[str, dict[str, int]] = defaultdict(dict)
    for (pattern_type, decision), count in sorted(by_type_decision.items()):
        by_type[pattern_type][decision] = count
    return {
        "by_decision": dict(sorted(Counter(row.get("decision") or "unknown" for row in rows).items())),
        "by_type": dict(sorted(by_type.items())),
    }


def count_non_evidence_reasons(rows: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows:
        for reason in row.get("non_evidence_reasons") or []:
            counts[str(reason)] += 1
    return [{"reason": reason, "count": count} for reason, count in counts.most_common(limit)]


def recent_llm_reviews(rows: list[dict[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: str(row.get("reviewed_at") or ""))
    return [
        {
            "document_id": row.get("document_id"),
            "pattern_id": row.get("pattern_id"),
            "pattern_type": row.get("pattern_type"),
            "decision": row.get("decision"),
            "confidence": row.get("confidence"),
            "reason": row.get("reason"),
        }
        for row in ordered[-limit:]
    ]


def markdown_llm_review_summary(summary: dict[str, Any]) -> str:
    title = "LLM Vetting Summary"
    if summary.get("document_id"):
        title += f": {summary['document_id']}"

    lines = [
        f"# {title}",
        "",
        f"- rows: {summary['row_count']}",
        f"- latest reviewed patterns: {summary['latest_pattern_count']}",
        f"- parse errors: {len(summary['parse_errors'])}",
        "",
        "## Latest Decisions",
        "",
    ]
    for decision, count in summary["latest_decisions"]["by_decision"].items():
        lines.append(f"- `{decision}`: {count}")

    lines += ["", "## Type Breakdown", ""]
    for pattern_type, counts in summary["latest_decisions"]["by_type"].items():
        parts = [f"{decision} {count}" for decision, count in counts.items()]
        lines.append(f"- `{pattern_type}`: {', '.join(parts)}")

    lines += ["", "## Non-Evidence Reasons", ""]
    if summary["non_evidence_reasons"]:
        for item in summary["non_evidence_reasons"]:
            lines.append(f"- {item['reason']}: {item['count']}")
    else:
        lines.append("- None.")

    lines += ["", "## Recent Reviews", ""]
    if summary["recent_reviews"]:
        for row in summary["recent_reviews"]:
            lines.append(
                f"- `{row['pattern_type']}` {row['document_id']} `{row['pattern_id']}` "
                f"{row['decision']} ({row['confidence']}): {row['reason']}"
            )
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)
