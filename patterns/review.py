"""Review-decision rollups for pattern detector tuning."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .io import REVIEW_DECISIONS


POSITIVE_DECISIONS = {"accept", "accept_with_edits"}
NEGATIVE_DECISIONS = {"reject", "wrong_type", "useful_suggestion_not_supported"}
REVIEW_GAP_DECISIONS = {"missing_fields", "needs_more_context"}


def load_review_decisions(document_id: str | None = None, decisions_dir: Path = REVIEW_DECISIONS) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    paths = sorted(decisions_dir.glob("*.jsonl"))
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


def summarize_review_decisions(document_id: str | None = None) -> dict[str, Any]:
    rows, errors = load_review_decisions(document_id)
    latest = latest_decisions(rows)
    all_counts = count_rows(rows)
    latest_counts = count_rows(latest)
    conflicts = conflicting_decisions(rows)

    return {
        "document_id": document_id,
        "files_read": sorted({row["_file"] for row in rows}),
        "row_count": len(rows),
        "latest_pattern_count": len(latest),
        "parse_errors": errors,
        "all_decisions": all_counts,
        "latest_decisions": latest_counts,
        "type_quality": type_quality(latest),
        "conflicts": conflicts,
        "notes": notable_notes(rows),
    }


def latest_decisions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_pattern: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("document_id") or ""), str(row.get("pattern_id") or ""))
        if not key[1]:
            continue
        current = by_pattern.get(key)
        if current is None or str(row.get("reviewed_at") or "") >= str(current.get("reviewed_at") or ""):
            by_pattern[key] = row
    return sorted(by_pattern.values(), key=lambda row: (row.get("document_id") or "", row.get("pattern_type") or "", row.get("pattern_id") or ""))


def count_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_type_decision = Counter((row.get("pattern_type") or "unknown", row.get("decision") or "unknown") for row in rows)
    by_type: dict[str, dict[str, int]] = defaultdict(dict)
    for (pattern_type, decision), count in sorted(by_type_decision.items()):
        by_type[pattern_type][decision] = count
    return {
        "by_decision": dict(sorted(Counter(row.get("decision") or "unknown" for row in rows).items())),
        "by_type": dict(sorted(by_type.items())),
    }


def type_quality(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row.get("pattern_type") or "unknown"].append(row)

    out: dict[str, dict[str, Any]] = {}
    for pattern_type, type_rows in sorted(grouped.items()):
        accepted = sum(1 for row in type_rows if row.get("decision") in POSITIVE_DECISIONS)
        rejected = sum(1 for row in type_rows if row.get("decision") in NEGATIVE_DECISIONS)
        review_gap = sum(1 for row in type_rows if row.get("decision") in REVIEW_GAP_DECISIONS)
        total = len(type_rows)
        out[pattern_type] = {
            "reviewed": total,
            "accepted": accepted,
            "rejected": rejected,
            "review_gap": review_gap,
            "acceptance_rate": round(accepted / total, 3) if total else None,
        }
    return out


def conflicting_decisions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (str(row.get("document_id") or ""), str(row.get("pattern_id") or ""))
        if key[1]:
            grouped[key].append(row)

    conflicts = []
    for (document_id, pattern_id), pattern_rows in sorted(grouped.items()):
        decisions = {row.get("decision") for row in pattern_rows}
        if len(decisions) <= 1:
            continue
        conflicts.append({
            "document_id": document_id,
            "pattern_id": pattern_id,
            "pattern_type": next((row.get("pattern_type") for row in reversed(pattern_rows) if row.get("pattern_type")), None),
            "decisions": sorted(decision for decision in decisions if decision),
            "latest": max(pattern_rows, key=lambda row: str(row.get("reviewed_at") or "")).get("decision"),
            "notes": [row.get("notes") for row in pattern_rows if row.get("notes")],
        })
    return conflicts


def notable_notes(rows: list[dict[str, Any]], limit: int = 60) -> list[dict[str, Any]]:
    noted = [row for row in rows if row.get("notes")]
    noted.sort(key=lambda row: str(row.get("reviewed_at") or ""))
    return [
        {
            "document_id": row.get("document_id"),
            "pattern_id": row.get("pattern_id"),
            "pattern_type": row.get("pattern_type"),
            "decision": row.get("decision"),
            "notes": row.get("notes"),
        }
        for row in noted[-limit:]
    ]


def markdown_review_summary(summary: dict[str, Any]) -> str:
    title = "Review Decision Summary"
    if summary.get("document_id"):
        title += f": {summary['document_id']}"

    lines = [
        f"# {title}",
        "",
        f"- rows: {summary['row_count']}",
        f"- latest reviewed patterns: {summary['latest_pattern_count']}",
        f"- parse errors: {len(summary['parse_errors'])}",
        "",
        "## Latest Type Quality",
        "",
    ]
    for pattern_type, quality in summary["type_quality"].items():
        rate = quality["acceptance_rate"]
        rate_text = f"{rate:.3f}" if isinstance(rate, float) else "n/a"
        lines.append(
            f"- `{pattern_type}`: {quality['accepted']}/{quality['reviewed']} accepted "
            f"(rate {rate_text}); {quality['rejected']} rejected; {quality['review_gap']} needs more context/missing fields"
        )

    lines += ["", "## Conflicts", ""]
    if summary["conflicts"]:
        for conflict in summary["conflicts"][:40]:
            lines.append(
                f"- `{conflict['pattern_type']}` {conflict['document_id']} `{conflict['pattern_id']}`: "
                f"{', '.join(conflict['decisions'])}; latest `{conflict['latest']}`"
            )
    else:
        lines.append("- None.")

    lines += ["", "## Recent Notes", ""]
    if summary["notes"]:
        for note in summary["notes"][-25:]:
            lines.append(
                f"- `{note['pattern_type']}` {note['document_id']} `{note['pattern_id']}` "
                f"{note['decision']}: {note['notes']}"
            )
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)
