"""Command-line harness for the pattern-identification worktrack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .detectors import detect
from .graph import build_graph, write_graph
from .io import (
    CORPUS_MANIFEST,
    OUT,
    REGISTRY,
    REPORTS,
    corpus_from_rk3_list,
    ensure_dirs,
    load_ir,
    read_json,
    write_json,
    write_text,
)
from .report import build_report, markdown_summary
from .review import markdown_review_summary, summarize_review_decisions
from .validate import validate_report_against_registry
from .vet import vet_candidates


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="pattern-id")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="show the resolved IR input for a document or artifact")
    ingest.add_argument("document_artifact")

    analyze = sub.add_parser("analyze", help="run deterministic pattern detection")
    analyze.add_argument("document_id")

    report = sub.add_parser("report", help="write a markdown review report from an existing JSON report")
    report.add_argument("document_id")

    validate = sub.add_parser("validate", help="validate one generated JSON report against the registry contract")
    validate.add_argument("document_id")

    eval_cmd = sub.add_parser("eval", help="compare candidates to gold annotations")
    eval_cmd.add_argument("document_id", nargs="?")
    eval_cmd.add_argument("--all", action="store_true")

    manifest = sub.add_parser("manifest", help="print manifest status")
    manifest.add_argument("--refresh-from-rk3", action="store_true")

    review_summary = sub.add_parser("review-summary", help="summarize JSONL reviewer decisions")
    review_summary.add_argument("document_id", nargs="?")
    review_summary.add_argument("--markdown", action="store_true")

    graph = sub.add_parser("graph", help="emit a graph JSON from one or more pattern reports")
    graph.add_argument("document_id", nargs="*")
    graph.add_argument("--all", action="store_true")
    graph.add_argument("--write", type=Path)

    vet = sub.add_parser("vet", help="LLM first-pass vetting for deterministic pattern candidates")
    vet.add_argument("document_id")
    vet.add_argument("--pattern-type")
    vet.add_argument("--limit", type=int)
    vet.add_argument("--batch-size", type=int, default=12)
    vet.add_argument("--provider")
    vet.add_argument("--model")
    vet.add_argument("--write", action="store_true")
    vet.add_argument("--dry-run", action="store_true")
    vet.add_argument("--skip-human-reviewed", action="store_true")

    args = parser.parse_args(argv)
    ensure_dirs()

    if args.command == "ingest":
        document_id, path, ir = load_ir(args.document_artifact)
        print(json.dumps({
            "document_id": document_id,
            "ir": str(path),
            "irVersion": ir.get("irVersion"),
            "pages": len(ir.get("pages") or {}),
        }, indent=2))
    elif args.command == "analyze":
        path = analyze_document(args.document_id)
        print(path)
    elif args.command == "report":
        print(write_markdown_report(args.document_id))
    elif args.command == "validate":
        errors = validate_document_report(args.document_id)
        print(json.dumps({"document_id": args.document_id, "ok": not errors, "errors": errors}, indent=2, sort_keys=True))
        if errors:
            raise SystemExit(1)
    elif args.command == "eval":
        print(json.dumps(eval_gold(args.document_id, all_docs=args.all), indent=2, sort_keys=True))
    elif args.command == "manifest":
        print(json.dumps(manifest_status(refresh=args.refresh_from_rk3), indent=2, sort_keys=True))
    elif args.command == "review-summary":
        summary = summarize_review_decisions(args.document_id)
        if args.markdown:
            print(markdown_review_summary(summary))
        else:
            print(json.dumps(summary, indent=2, sort_keys=True))
    elif args.command == "graph":
        graph_data = build_graph(None if args.all else args.document_id)
        if args.write:
            print(write_graph(graph_data, args.write))
        else:
            print(json.dumps(graph_data, indent=2, sort_keys=True))
    elif args.command == "vet":
        print(json.dumps(vet_candidates(
            args.document_id,
            pattern_type=args.pattern_type,
            limit=args.limit,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            write=args.write,
            provider=args.provider,
            model=args.model,
            skip_human_reviewed=args.skip_human_reviewed,
        ), indent=2, sort_keys=True))


def registry_by_id() -> dict[str, dict]:
    data = read_json(REGISTRY)
    return {entry["id"]: entry for entry in data["patterns"]}


def analyze_document(document_id_or_path: str) -> Path:
    document_id, ir_path, ir = load_ir(document_id_or_path)
    candidates = detect(ir, document_id, registry_by_id())
    report = build_report(document_id, ir_path, ir, candidates)
    out_path = OUT / f"{document_id}.json"
    write_json(out_path, report)
    write_text(REPORTS / f"{document_id}.md", markdown_summary(report))
    return out_path


def write_markdown_report(document_id: str) -> Path:
    report_path = OUT / f"{document_id}.json"
    if not report_path.exists():
        analyze_document(document_id)
    report = read_json(report_path)
    out = REPORTS / f"{document_id}.md"
    write_text(out, markdown_summary(report))
    return out


def validate_document_report(document_id: str) -> list[str]:
    report_path = OUT / f"{document_id}.json"
    if not report_path.exists():
        analyze_document(document_id)
    return validate_report_against_registry(read_json(report_path), read_json(REGISTRY))


def manifest_status(refresh: bool = False) -> dict:
    manifest = read_json(CORPUS_MANIFEST)
    discovered = corpus_from_rk3_list() if refresh else []
    return {
        "manifest_documents": len(manifest.get("documents") or []),
        "pilot_documents": manifest.get("pilot_documents", []),
        "rk3_discovered": discovered,
    }


def eval_gold(document_id: str | None, all_docs: bool = False) -> dict:
    gold_dir = Path(__file__).resolve().parent / "gold"
    docs = [p.stem for p in gold_dir.glob("*.json")] if all_docs else [document_id]
    docs = [doc for doc in docs if doc]
    results = {}
    for doc in docs:
        report_path = OUT / f"{doc}.json"
        if not report_path.exists():
            analyze_document(doc)
        report = read_json(report_path)
        gold_path = gold_dir / f"{doc}.json"
        if not gold_path.exists():
            results[doc] = {"error": "no gold annotations"}
            continue
        gold = read_json(gold_path)
        found_types = {c["pattern_type"] for c in report["candidates"]}
        gold_rows = gold.get("annotations", [])
        positive_rows = [a for a in gold_rows if a.get("expected", True)]
        negative_rows = [a for a in gold_rows if not a.get("expected", True)]
        expected_types = {a["pattern_type"] for a in positive_rows}
        gold_matches = [gold_match(row, report.get("candidates", [])) for row in positive_rows]
        negative_matches = [gold_match(row, report.get("candidates", [])) for row in negative_rows]
        results[doc] = {
            "expected_types": sorted(expected_types),
            "found_types": sorted(found_types),
            "type_recall": round(len(expected_types & found_types) / len(expected_types), 3) if expected_types else None,
            "source_hit_rate": round(sum(1 for m in gold_matches if m["matched"]) / len(gold_matches), 3) if gold_matches else None,
            "negative_hit_count": sum(1 for m in negative_matches if m["matched"]),
            "gold_matches": gold_matches,
            "negative_matches": negative_matches,
            "candidate_count": len(report["candidates"]),
            "gold_count": len(positive_rows),
            "negative_gold_count": len(negative_rows),
        }
    return results


def gold_match(row: dict, candidates: list[dict]) -> dict:
    needle = normalize_text(row.get("source_text") or "")
    row_type = row.get("pattern_type")
    row_page = row.get("page")
    for candidate in candidates:
        if candidate.get("pattern_type") != row_type:
            continue
        refs = candidate.get("source_refs") or []
        if row_page is not None and refs and refs[0].get("page") != row_page:
            continue
        haystack = normalize_text(" ".join(candidate_text_parts(candidate)))
        if not needle or needle in haystack or haystack in needle:
            return {"pattern_type": row_type, "page": row_page, "source_text": row.get("source_text"), "matched": True, "pattern_id": candidate.get("pattern_id")}
    return {"pattern_type": row_type, "page": row_page, "source_text": row.get("source_text"), "matched": False, "pattern_id": None}


def candidate_text_parts(candidate: dict) -> list[str]:
    parts = []
    for ref in candidate.get("source_refs") or []:
        parts.append(str(ref.get("quote") or ""))
    fields = candidate.get("fields") or {}
    parts.extend(str(v) for v in fields.values() if isinstance(v, (str, int, float)))
    for metric in fields.get("metrics") or []:
        parts.extend(str(v) for v in metric.values() if v is not None)
    parts.extend(str(step) for step in fields.get("steps") or [])
    return parts


def normalize_text(text: str) -> str:
    return "".join(ch.lower() for ch in str(text) if ch.isalnum())


if __name__ == "__main__":
    main(sys.argv[1:])
