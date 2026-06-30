"""Source-document discovery and status reporting."""

import json
import re
import shutil
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
        # "docs" holds prose; "inactive/…" holds parked/atypical sources we don't
        # process (the */*.pdf glob already skips inactive's deeper nesting, but
        # guard a PDF dropped directly in sources/inactive/ too)
        if folder in ("docs", "inactive"):
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


# per-document sidecar files that live next to the source PDF
_SIDECARS = (".config.json", ".ops.json", ".landing.json", ".landing-theme.json", ".landing-ai.json")


def resolve_slug(arg: str) -> str:
    """Accept a slug, a PDF filename, or a path; return the slug. Falls back to
    the arg itself (so orphaned output can still be cleaned by slug)."""
    for d in list_documents():
        if arg in (d["slug"], d["name"]) or d["path"] == arg or d["path"].endswith("/" + arg):
            return d["slug"]
    return arg


def document_artifacts(slug: str) -> list[Path]:
    """Every existing artifact derived from a document (read-only; for listing)."""
    paths = []
    src = source_for_slug(slug)
    if src:
        paths.append(src)
        paths += [src.with_name(src.stem + s) for s in _SIDECARS]
    paths.append(output_dir(slug))
    paths.append(ROOT / "feedback" / f"{slug}.jsonl")
    return [p for p in paths if p.exists()]


def remove_document(slug: str) -> list[Path]:
    """Delete a document and all its derived artifacts. Returns what was removed."""
    removed = []
    for p in document_artifacts(slug):
        shutil.rmtree(p) if p.is_dir() else p.unlink()
        removed.append(p)
    return removed


def _status(slug: str) -> dict:
    pages_dir = output_dir(slug) / "pages"
    n_pages = len(list(pages_dir.glob("page-*.png"))) if pages_dir.is_dir() else 0
    meta_path = output_dir(slug) / "meta.json"
    if not meta_path.exists():
        return {"status": "unconverted", "pages": n_pages}
    try:
        meta = json.loads(meta_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"status": "unconverted"}
    return {
        "status": meta.get("status", "unconverted"),  # in_progress | done | failed
        "error": meta.get("error"),
        "finished": meta.get("finished"),
        "pages": n_pages,
    }
