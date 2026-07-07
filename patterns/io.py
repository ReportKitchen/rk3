"""File IO helpers for the pattern-identification CLI."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PATTERNS = ROOT / "patterns"
OUT = PATTERNS / "out"
REPORTS = PATTERNS / "reports"
LOGS = PATTERNS / "logs"
LLM_REVIEWS = PATTERNS / "llm-reviews"
REVIEW_DECISIONS = PATTERNS / "review-decisions"
CORPUS_MANIFEST = PATTERNS / "corpus" / "manifest.json"
REGISTRY = PATTERNS / "registry" / "patterns.json"


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    LLM_REVIEWS.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def ir_path_for(document_id: str) -> Path:
    candidate = Path(document_id)
    if candidate.exists():
        return candidate
    return ROOT / "output" / "pdfium" / document_id / "ir.json"


def document_id_from_ir_path(path: Path) -> str:
    if path.name == "ir.json" and path.parent.parent.name == "pdfium":
        return path.parent.name
    return path.stem


def load_ir(document_id_or_path: str) -> tuple[str, Path, dict]:
    path = ir_path_for(document_id_or_path)
    if not path.exists():
        raise SystemExit(f"IR not found: {path}")
    return document_id_from_ir_path(path), path, read_json(path)


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def corpus_from_rk3_list() -> list[dict]:
    """Use the plan-sanctioned CLI to discover corpus docs without rk3 imports."""
    try:
        proc = subprocess.run(
            ["python3", "-m", "rk3", "list"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    docs = []
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            docs.append({"status": parts[0], "document_id": parts[1]})
    return docs
