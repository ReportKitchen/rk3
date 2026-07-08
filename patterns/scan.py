"""LLM-originated pattern scanning for development comparison."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rk3 import irwalk
from rk3.ai import complete_json, get_ai_config
from rk3.prompts import load_prompt

from .io import LLM_SCANS, OUT, REGISTRY, load_ir, read_json


LANDING_SCAN_PATTERN_TYPES = {
    "statistic",
    "impact_statement",
    "funding_event",
    "quotation",
    "key_finding",
    "recommendation",
}


STATISTIC_VALUE_RE = re.compile(
    r"[$]?\d(?:[\d,]*\d)?(?:\.\d+)?|"
    r"\b(?:one[- ]third|two[- ]thirds|one[- ]quarter|one[- ]fourth|three[- ]quarters|one[- ]half|half)\b",
    re.I,
)


SCAN_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pattern_type": {"type": "string"},
                    "page": {"type": ["integer", "null"]},
                    "quote": {"type": "string"},
                    "label": {"type": ["string", "null"]},
                    "fields": {"type": "object"},
                    "confidence": {"type": "number"},
                    "reason": {"type": "string"},
                    "evidence_in_real_world": {"type": "boolean"},
                },
                "required": [
                    "pattern_type",
                    "page",
                    "quote",
                    "label",
                    "fields",
                    "confidence",
                    "reason",
                    "evidence_in_real_world",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}


def scan_document(
    document_id: str,
    *,
    pages: list[int] | None = None,
    pattern_type: str | None = None,
    limit_findings: int = 20,
    max_chars: int = 14000,
    dry_run: bool = False,
    write: bool = False,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    document_id, ir_path, ir = load_ir(document_id)
    catalog = pattern_catalog(pattern_type)
    excerpt = document_excerpt(ir, pages=pages, max_chars=max_chars)
    config = get_ai_config()
    out: dict[str, Any] = {
        "document_id": document_id,
        "ir": str(ir_path),
        "pages": pages or sorted({item["page"] for item in excerpt["items"] if item.get("page")}),
        "excerpt_chars": excerpt["char_count"],
        "truncated": excerpt["truncated"],
        "provider": provider or config["provider"],
        "model": model or config["model"],
        "dry_run": dry_run,
        "findings": [],
    }
    prompt = build_scan_prompt(document_id, catalog, excerpt, limit_findings)
    if dry_run:
        out["prompt_preview"] = prompt
        return out

    response = complete_json(
        load_prompt("patterns/scan-document.system.md"),
        prompt,
        SCAN_SCHEMA,
        max_tokens=5000,
        provider=provider,
        model=model,
    )
    deterministic = deterministic_candidates(document_id)
    out["findings"] = normalize_findings(
        document_id,
        response.get("findings", []),
        catalog,
        out["provider"],
        out["model"],
        deterministic,
    )
    if write and out["findings"]:
        path = write_llm_scan(document_id, out["findings"])
        out["write_path"] = str(path)
    return out


def pattern_catalog(pattern_type: str | None = None) -> list[dict[str, Any]]:
    registry = read_json(REGISTRY)
    out = []
    for entry in registry.get("patterns") or []:
        if pattern_type and entry.get("id") != pattern_type:
            continue
        if not pattern_type and entry.get("id") not in LANDING_SCAN_PATTERN_TYPES:
            continue
        out.append({
            "pattern_type": entry.get("id"),
            "name": entry.get("name"),
            "layer": str(entry.get("layer")),
            "definition": entry.get("definition") or "",
            "positive_indicators": entry.get("positive_indicators") or [],
            "negative_indicators": entry.get("negative_indicators") or [],
            "required_fields": entry.get("required_fields") or [],
            "optional_fields": entry.get("optional_fields") or [],
            "evidence_requirements": entry.get("evidence_requirements") or [],
            "common_false_positives": entry.get("common_false_positives") or [],
        })
    return out


def document_excerpt(ir: dict, *, pages: list[int] | None, max_chars: int) -> dict[str, Any]:
    selected_pages = set(pages or [])
    items = []
    total = 0
    truncated = False
    for node in irwalk.leaves(ir.get("body") or []):
        text = clean_excerpt_text(node.get("text") or "")
        page = node.get("page")
        if not text or (selected_pages and page not in selected_pages):
            continue
        block = {"page": page, "nid": node.get("nid"), "text": text}
        line = json.dumps(block, sort_keys=True)
        if total + len(line) + 1 > max_chars:
            truncated = True
            break
        items.append(block)
        total += len(line) + 1
    return {"items": items, "char_count": total, "truncated": truncated}


def build_scan_prompt(document_id: str, catalog: list[dict[str, str]], excerpt: dict[str, Any], limit_findings: int) -> str:
    payload = {
        "document_id": document_id,
        "limit_findings": limit_findings,
        "pattern_catalog": catalog,
        "document_excerpt": excerpt["items"],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def deterministic_candidates(document_id: str) -> list[dict[str, Any]]:
    path = OUT / f"{document_id}.json"
    if not path.exists():
        return []
    return read_json(path).get("candidates") or []


def normalize_findings(
    document_id: str,
    findings: list[dict[str, Any]],
    catalog: list[dict[str, str]],
    provider: str,
    model: str,
    deterministic: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    allowed = {entry["pattern_type"] for entry in catalog}
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for finding in findings:
        pattern_type = str(finding.get("pattern_type") or "")
        quote = clean_excerpt_text(finding.get("quote") or "")
        if pattern_type not in allowed or not quote:
            continue
        fields = finding.get("fields") or {}
        if pattern_type == "statistic" and not has_statistic_value(fields, quote):
            continue
        overlap = best_deterministic_overlap(pattern_type, quote, deterministic)
        out.append({
            "schema": 1,
            "document_id": document_id,
            "scan_id": scan_id(document_id, pattern_type, finding.get("page"), quote),
            "pattern_type": pattern_type,
            "page": finding.get("page"),
            "quote": quote,
            "label": finding.get("label"),
            "fields": fields,
            "confidence": finding.get("confidence"),
            "reason": finding.get("reason"),
            "evidence_in_real_world": finding.get("evidence_in_real_world"),
            "reviewer": "llm",
            "reviewed_at": now,
            "provider": provider,
            "model": model,
            "deterministic_overlap": overlap,
        })
    return out


def has_statistic_value(fields: dict[str, Any], quote: str) -> bool:
    for key in ("value", "amount", "percentage", "share", "count", "rate"):
        value = fields.get(key)
        if value is not None and str(value).strip():
            return True
    return bool(STATISTIC_VALUE_RE.search(quote or ""))


def best_deterministic_overlap(pattern_type: str, quote: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    best = None
    for candidate in candidates:
        candidate_quote = ((candidate.get("source_refs") or [{}])[0].get("quote") or "")
        score = token_overlap_score(quote, candidate_quote)
        if score < 0.45:
            continue
        if candidate.get("pattern_type") == pattern_type:
            score += 0.15
        if best is None or score > best["score"]:
            best = {
                "pattern_id": candidate.get("pattern_id"),
                "pattern_type": candidate.get("pattern_type"),
                "score": round(min(score, 1.0), 3),
            }
    return best


def token_overlap_score(left: str, right: str) -> float:
    left_tokens = set(tokens(left))
    right_tokens = set(tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(token) > 2]


def scan_id(document_id: str, pattern_type: str, page: Any, quote: str) -> str:
    raw = json.dumps([document_id, pattern_type, page, quote[:240]], sort_keys=True)
    return "scan_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def clean_excerpt_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def write_llm_scan(document_id: str, findings: list[dict[str, Any]]) -> Path:
    LLM_SCANS.mkdir(parents=True, exist_ok=True)
    path = LLM_SCANS / f"{document_id}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        for finding in findings:
            handle.write(json.dumps(finding, sort_keys=True) + "\n")
    return path


def load_llm_scans(document_id: str | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    paths = sorted(LLM_SCANS.glob("*.jsonl"))
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


def summarize_llm_scans(document_id: str | None = None) -> dict[str, Any]:
    rows, errors = load_llm_scans(document_id)
    latest = latest_scan_findings(rows)
    return {
        "document_id": document_id,
        "files_read": sorted({row["_file"] for row in rows}),
        "row_count": len(rows),
        "latest_finding_count": len(latest),
        "parse_errors": errors,
        "by_type": dict(sorted(Counter(row.get("pattern_type") or "unknown" for row in latest).items())),
        "overlap": overlap_counts(latest),
        "recent_findings": recent_scan_findings(latest),
    }


def latest_scan_findings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("document_id") or ""), str(row.get("scan_id") or ""))
        if not key[1]:
            continue
        current = by_id.get(key)
        if current is None or str(row.get("reviewed_at") or "") >= str(current.get("reviewed_at") or ""):
            by_id[key] = row
    return sorted(by_id.values(), key=lambda row: (row.get("document_id") or "", row.get("pattern_type") or "", row.get("scan_id") or ""))


def overlap_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    same_type = 0
    other_type = 0
    llm_only = 0
    for row in rows:
        overlap = row.get("deterministic_overlap")
        if not overlap:
            llm_only += 1
        elif overlap.get("pattern_type") == row.get("pattern_type"):
            same_type += 1
        else:
            other_type += 1
    return {"same_type_overlap": same_type, "other_type_text_overlap": other_type, "llm_only": llm_only}


def recent_scan_findings(rows: list[dict[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: str(row.get("reviewed_at") or ""))
    return [
        {
            "document_id": row.get("document_id"),
            "scan_id": row.get("scan_id"),
            "pattern_type": row.get("pattern_type"),
            "page": row.get("page"),
            "confidence": row.get("confidence"),
            "overlap": row.get("deterministic_overlap"),
            "quote": row.get("quote"),
            "reason": row.get("reason"),
        }
        for row in ordered[-limit:]
    ]


def markdown_llm_scan_summary(summary: dict[str, Any]) -> str:
    title = "LLM Scan Summary"
    if summary.get("document_id"):
        title += f": {summary['document_id']}"
    lines = [
        f"# {title}",
        "",
        f"- rows: {summary['row_count']}",
        f"- latest findings: {summary['latest_finding_count']}",
        f"- parse errors: {len(summary['parse_errors'])}",
        f"- same-type deterministic overlap: {summary['overlap']['same_type_overlap']}",
        f"- other-type text overlap: {summary['overlap']['other_type_text_overlap']}",
        f"- LLM-only: {summary['overlap']['llm_only']}",
        "",
        "## Type Breakdown",
        "",
    ]
    for pattern_type, count in summary["by_type"].items():
        lines.append(f"- `{pattern_type}`: {count}")
    lines += ["", "## Recent Findings", ""]
    if summary["recent_findings"]:
        for row in summary["recent_findings"]:
            overlap = row.get("overlap")
            if overlap and overlap["pattern_type"] == row["pattern_type"]:
                overlap_text = f" same-type overlap `{overlap['pattern_id']}` ({overlap['score']})"
            elif overlap:
                overlap_text = f" text overlap `{overlap['pattern_type']}` `{overlap['pattern_id']}` ({overlap['score']})"
            else:
                overlap_text = " LLM-only"
            lines.append(
                f"- `{row['pattern_type']}` p{row['page']} `{row['scan_id']}` "
                f"({row['confidence']}){overlap_text}: {row['quote']} :: {row['reason']}"
            )
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)
