"""The bridge that lets the slug-based landing engine serve PLATFORM documents.

Corpus docs live under sources/ and are addressed by slug; platform docs are
UUID-keyed rows with files in private storage. Everything landing-related
(`_ir_for`, `_landing_path`, social-post paths, asset URLs) resolves through
here when the "slug" is a document UUID, so the whole Assemble/Wordsmith/
Publish engine works for customer uploads unchanged.

Local-backend note: landing caches are read/written as local files (same as
the corpus). When storage flips to S3 the landing cache IO needs a
storage-adapter pass — recorded in the execution plan.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from sqlalchemy import select

from rk3.platform.db import session_scope
from rk3.platform.models import Document, Run
from rk3.platform.storage import LocalDiskStorage

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def is_platform_doc(slug: str) -> bool:
    return bool(_UUID_RE.match(slug or ""))


def doc_info(doc_id: str) -> dict | None:
    """{id, name, workspace_id, project_id, status, doc_dir, run_dir|None,
    source} for a platform document — local filesystem paths."""
    with session_scope() as db:
        doc = db.get(Document, uuid.UUID(doc_id))
        if doc is None or doc.legacy:
            return None
        run = db.execute(
            select(Run).where(Run.document_id == doc.id, Run.status == "succeeded")
            .order_by(Run.created_at.desc())).scalars().first()
        storage = LocalDiskStorage()
        doc_dir = storage.path(doc.storage_key).parent if doc.storage_key else None
        return {
            "id": str(doc.id), "name": doc.name,
            "workspace_id": doc.workspace_id, "project_id": doc.project_id,
            "status": doc.status,
            "doc_dir": doc_dir,
            "run_dir": storage.path(run.storage_prefix) if run else None,
            "source": storage.path(doc.storage_key) if doc.storage_key else None,
        }


def landing_dir(doc_id: str) -> Path:
    """Where a platform document's landing caches live (private, beside the
    source): .../documents/<id>/landing/"""
    info = doc_info(doc_id)
    if info is None or info["doc_dir"] is None:
        raise FileNotFoundError(f"unknown platform document {doc_id}")
    d = info["doc_dir"] / "landing"
    d.mkdir(parents=True, exist_ok=True)
    return d


def files_base(doc_id: str) -> str:
    """The membership-checked asset base for this doc (client assetBase)."""
    return f"/api/platform/documents/{doc_id}/files"
