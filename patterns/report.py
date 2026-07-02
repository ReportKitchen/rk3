"""Report assembly and markdown rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import REPORT_SCHEMA_VERSION
from .detectors import inventory, page_inventory
from .io import iso_mtime


def build_report(document_id: str, ir_path: Path, ir: dict, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA_VERSION,
        "document_id": document_id,
        "document": {
            "title": ir.get("title"),
            "page_count": len(ir.get("pages") or {}),
        },
        "input": {
            "artifact": str(ir_path.relative_to(ir_path.parents[2])) if len(ir_path.parents) >= 3 else str(ir_path),
            "irVersion": ir.get("irVersion"),
            "convertedAt": iso_mtime(ir_path),
        },
        "pattern_inventory": inventory(candidates),
        "page_inventory": page_inventory(candidates),
        "candidates": candidates,
        "evaluation_notes": [],
        "warnings": [],
    }


def markdown_summary(report: dict[str, Any]) -> str:
    lines = [
        f"# Pattern Review: {report['document_id']}",
        "",
        f"- schema: {report['schema']}",
        f"- title: {report['document'].get('title') or ''}",
        f"- pages: {report['document'].get('page_count')}",
        f"- irVersion: {report['input'].get('irVersion')}",
        f"- convertedAt: {report['input'].get('convertedAt')}",
        "",
        "## Inventory",
        "",
    ]
    if report["pattern_inventory"]:
        for pattern_type, count in report["pattern_inventory"].items():
            lines.append(f"- {pattern_type}: {count}")
    else:
        lines.append("- No candidates detected.")

    lines += ["", "## Review Focus", ""]
    lines += review_focus_lines(report["candidates"])

    lines += ["", "## High Confidence Candidates", ""]
    high = [c for c in report["candidates"] if c["confidence"] >= 0.75][:40]
    lines += candidate_lines(high)

    lines += ["", "## Lower Confidence Candidates", ""]
    low = [c for c in report["candidates"] if c["confidence"] < 0.75][:40]
    lines += candidate_lines(low)

    lines += [
        "",
        "## Reviewer Questions",
        "",
        "- Which candidate types are useful enough to keep in the first review tab?",
        "- Which repeated false positives should become validation rules?",
        "- Are any component recommendations unsafe without editorial review?",
        "",
    ]
    return "\n".join(lines)


def review_focus_lines(candidates: list[dict[str, Any]]) -> list[str]:
    if not candidates:
        return ["- None."]
    focus = []
    by_type: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        by_type.setdefault(candidate["pattern_type"], []).append(candidate)
    for pattern_type, rows in sorted(by_type.items()):
        top = sorted(rows, key=lambda c: c.get("confidence", 0), reverse=True)[:3]
        sample = "; ".join(display_value(c) for c in top)
        focus.append(f"- `{pattern_type}`: {len(rows)} candidate(s). Sample: {sample}")
    return focus


def candidate_lines(candidates: list[dict[str, Any]]) -> list[str]:
    if not candidates:
        return ["- None."]
    lines = []
    for candidate in candidates:
        ref = candidate["source_refs"][0]
        value = display_value(candidate)
        quote = ref.get("quote") or ""
        if quote and quote != value:
            value = f"{value} | source: {quote}"
        lines.append(
            f"- `{candidate['pattern_type']}` p{ref.get('page')} "
            f"`{candidate['pattern_id']}` ({candidate['confidence']:.2f}): {value}"
        )
    return lines


def display_value(candidate: dict[str, Any]) -> str:
    fields = candidate.get("fields") or {}
    pattern_type = candidate.get("pattern_type")
    if pattern_type == "named_entity":
        return fields.get("entity_text") or first_quote(candidate)
    if pattern_type == "statistic":
        bits = [fields.get("value"), fields.get("unit"), fields.get("label")]
        return " ".join(str(b) for b in bits if b)
    if pattern_type == "funding_event":
        bits = [fields.get("amount"), fields.get("funder"), fields.get("program"), fields.get("recipient")]
        return " -> ".join(str(b) for b in bits if b)
    if pattern_type == "impact_statement":
        bits = [fields.get("impact_type"), fields.get("value"), fields.get("statement_text")]
        return " | ".join(str(b) for b in bits if b)
    if pattern_type == "legal_reference":
        return fields.get("reference_text") or first_quote(candidate)
    if pattern_type == "resource":
        bits = [fields.get("resource_name"), fields.get("resource_type")]
        return " | ".join(str(b) for b in bits if b)
    if pattern_type == "callout_label":
        return fields.get("label_text") or first_quote(candidate)
    if pattern_type == "entity_relationship":
        subject = fields.get("subject")
        predicate = fields.get("predicate")
        obj = fields.get("object")
        if subject and predicate and obj:
            return f"{subject} --{predicate}--> {obj}"
    if pattern_type == "metric_cluster":
        metrics = fields.get("metrics") or []
        values = [m.get("value") for m in metrics if m.get("value")]
        return f"{len(metrics)} metric(s): " + ", ".join(values[:6])
    if pattern_type == "process_step_list":
        steps = fields.get("steps") or []
        return f"{len(steps)} step(s): " + "; ".join(steps[:3])
    for key in ("question_text", "quote_text", "callout_text", "finding_text", "action", "value", "place", "term"):
        if fields.get(key):
            return str(fields[key])
    return first_quote(candidate)


def first_quote(candidate: dict[str, Any]) -> str:
    refs = candidate.get("source_refs") or []
    return (refs[0].get("quote") if refs else "") or ""
