"""Build graph-ready nodes and edges from pattern reports."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .io import OUT, read_json, write_json


def build_graph(document_ids: list[str] | None = None) -> dict[str, Any]:
    reports = load_reports(document_ids)
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}

    def add_node(kind: str, label: str | None, candidate: dict[str, Any] | None = None, subtype: str | None = None) -> str | None:
        if not label:
            return None
        label = clean_label(label)
        if not label:
            return None
        node_id = stable_graph_id("node", kind, label)
        node = nodes.setdefault(node_id, {
            "id": node_id,
            "kind": kind,
            "label": label,
            "subtype": subtype,
            "mentions": 0,
            "documents": [],
            "pages": [],
            "candidate_ids": [],
        })
        node["mentions"] += 1
        if subtype and not node.get("subtype"):
            node["subtype"] = subtype
        if candidate:
            doc = candidate.get("_document_id")
            page = first_page(candidate)
            append_unique(node["documents"], doc)
            append_unique(node["pages"], page)
            append_unique(node["candidate_ids"], candidate.get("pattern_id"))
        return node_id

    def add_edge(source: str | None, target: str | None, predicate: str, candidate: dict[str, Any], evidence: str | None = None) -> None:
        if not source or not target or source == target:
            return
        edge_id = stable_graph_id("edge", source, predicate, target)
        edge = edges.setdefault(edge_id, {
            "id": edge_id,
            "source": source,
            "target": target,
            "predicate": predicate,
            "documents": [],
            "pages": [],
            "candidate_ids": [],
            "evidence": [],
        })
        append_unique(edge["documents"], candidate.get("_document_id"))
        append_unique(edge["pages"], first_page(candidate))
        append_unique(edge["candidate_ids"], candidate.get("pattern_id"))
        append_unique(edge["evidence"], evidence or first_quote(candidate))

    for report in reports:
        for candidate in report.get("candidates") or []:
            candidate["_document_id"] = report.get("document_id")
            fields = candidate.get("fields") or {}
            pattern_type = candidate.get("pattern_type")

            if pattern_type == "named_entity":
                add_node(fields.get("entity_type") or "entity", fields.get("entity_text"), candidate)
            elif pattern_type == "resource":
                add_node("resource", fields.get("resource_name"), candidate, fields.get("resource_type"))
            elif pattern_type == "geography_place":
                add_node("place", fields.get("place"), candidate, fields.get("place_type"))
            elif pattern_type == "legal_reference":
                add_node("legal_reference", fields.get("reference_text"), candidate, fields.get("reference_type"))
            elif pattern_type == "entity_relationship":
                source = add_node(fields.get("subject_type") or "entity", fields.get("subject"), candidate)
                target = add_node(fields.get("object_type") or "entity", fields.get("object"), candidate)
                add_edge(source, target, fields.get("predicate") or "related_to", candidate)
            elif pattern_type == "funding_event":
                event = add_node("funding_event", funding_label(fields), candidate)
                funder = add_node("entity", fields.get("funder"), candidate)
                recipient = add_node("entity", fields.get("recipient"), candidate)
                program = add_node("resource", fields.get("program"), candidate, "fund")
                add_edge(funder, event, "funds", candidate)
                add_edge(event, recipient, "benefits", candidate)
                add_edge(event, program, "funds_program", candidate)
            elif pattern_type == "quotation":
                speaker = add_node("person", fields.get("speaker_name"), candidate)
                affiliation = add_node("organization", fields.get("speaker_affiliation"), candidate)
                add_edge(speaker, affiliation, "affiliated_with", candidate)

    return {
        "schema": 1,
        "documents": [report.get("document_id") for report in reports],
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": sorted(nodes.values(), key=lambda node: (node["kind"], node["label"])),
        "edges": sorted(edges.values(), key=lambda edge: (edge["predicate"], edge["source"], edge["target"])),
    }


def write_graph(graph: dict[str, Any], path: Path) -> Path:
    write_json(path, graph)
    return path


def load_reports(document_ids: list[str] | None = None) -> list[dict[str, Any]]:
    if document_ids:
        paths = [OUT / f"{doc}.json" for doc in document_ids]
    else:
        paths = sorted(OUT.glob("*.json"))
    reports = []
    for path in paths:
        if not path.exists():
            raise SystemExit(f"Pattern report not found: {path}")
        reports.append(read_json(path))
    return reports


def funding_label(fields: dict[str, Any]) -> str:
    bits = [fields.get("amount"), fields.get("program"), fields.get("purpose")]
    return " | ".join(str(bit) for bit in bits if bit) or "Funding event"


def first_page(candidate: dict[str, Any]) -> int | None:
    refs = candidate.get("source_refs") or []
    return refs[0].get("page") if refs else None


def first_quote(candidate: dict[str, Any]) -> str | None:
    refs = candidate.get("source_refs") or []
    return refs[0].get("quote") if refs else None


def clean_label(label: str) -> str:
    return re.sub(r"\s+", " ", str(label or "").strip(" ,.;:"))


def stable_graph_id(*parts: Any) -> str:
    seed = repr(parts)
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"graph_{digest}"


def append_unique(values: list[Any], value: Any) -> None:
    if value is not None and value not in values:
        values.append(value)
