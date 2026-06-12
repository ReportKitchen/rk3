"""Source-document discovery and status reporting."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
OUTPUT = ROOT / "output"

ENGINE = "pdfium"  # only engine for now; output layout is engine-aware already


def slugify(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return re.sub(r"-{2,}", "-", s)


def list_documents() -> list[dict]:
    docs = []
    for pdf in sorted(SOURCES.glob("*/*.pdf")):
        folder = pdf.parent.name
        if folder == "docs":
            continue
        slug = f"{folder}--{slugify(pdf.stem)}"
        docs.append({
            "slug": slug,
            "name": pdf.name,
            "folder": folder,
            "path": str(pdf),
            "hasConfig": pdf.with_name(pdf.stem + ".config.json").exists(),
            **_status(slug),
        })
    return docs


def source_for_slug(slug: str) -> Path | None:
    for d in list_documents():
        if d["slug"] == slug:
            return Path(d["path"])
    return None


def output_dir(slug: str) -> Path:
    return OUTPUT / ENGINE / slug


def _status(slug: str) -> dict:
    meta_path = output_dir(slug) / "meta.json"
    if not meta_path.exists():
        return {"status": "unconverted"}
    try:
        meta = json.loads(meta_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"status": "unconverted"}
    return {
        "status": meta.get("status", "unconverted"),  # in_progress | done | failed
        "error": meta.get("error"),
        "finished": meta.get("finished"),
    }
