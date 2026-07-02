"""Lightweight validation for pattern registry and generated reports."""

from __future__ import annotations

from typing import Any

from . import REPORT_SCHEMA_VERSION


REQUIRED_SOURCE_REF_KEYS = {"nid", "page", "quote"}
REQUIRED_CANDIDATE_KEYS = {
    "pattern_id", "pattern_type", "layer", "status", "confidence",
    "source_refs", "fields", "component_recommendations",
}


def validate_registry(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for i, entry in enumerate(registry.get("patterns") or []):
        pid = entry.get("id")
        if not pid:
            errors.append(f"registry.patterns[{i}] missing id")
            continue
        if pid in seen:
            errors.append(f"registry duplicate id: {pid}")
        seen.add(pid)
        for key in ("name", "layer", "definition", "required_fields", "evidence_requirements", "candidate_component_treatments"):
            if key not in entry:
                errors.append(f"registry.{pid} missing {key}")
    return errors


def validate_report(report: dict[str, Any], registry_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if report.get("schema") != REPORT_SCHEMA_VERSION:
        errors.append(f"report schema {report.get('schema')!r} != {REPORT_SCHEMA_VERSION}")
    if not report.get("document_id"):
        errors.append("report missing document_id")
    input_stamp = report.get("input") or {}
    if "irVersion" not in input_stamp:
        errors.append("report.input missing irVersion")
    if not input_stamp.get("convertedAt"):
        errors.append("report.input missing convertedAt")

    for i, candidate in enumerate(report.get("candidates") or []):
        missing = REQUIRED_CANDIDATE_KEYS - set(candidate)
        if missing:
            errors.append(f"candidates[{i}] missing {sorted(missing)}")
        pattern_type = candidate.get("pattern_type")
        if pattern_type not in registry_ids:
            errors.append(f"candidates[{i}] unknown pattern_type {pattern_type!r}")
        confidence = candidate.get("confidence")
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            errors.append(f"candidates[{i}] invalid confidence {confidence!r}")
        refs = candidate.get("source_refs") or []
        if not refs:
            errors.append(f"candidates[{i}] has no source_refs")
        for j, ref in enumerate(refs):
            missing_ref = REQUIRED_SOURCE_REF_KEYS - set(ref)
            if missing_ref:
                errors.append(f"candidates[{i}].source_refs[{j}] missing {sorted(missing_ref)}")
            if not ref.get("quote"):
                errors.append(f"candidates[{i}].source_refs[{j}] has empty quote")
    return errors


def validate_report_against_registry(report: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    registry_errors = validate_registry(registry)
    registry_ids = {entry.get("id") for entry in registry.get("patterns") or [] if entry.get("id")}
    return registry_errors + validate_report(report, registry_ids)
