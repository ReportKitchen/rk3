"""Private file storage behind an adapter — LocalDiskStorage now, S3 when AWS
exists. Keys follow the plan's layout exactly and contain only generated UUIDs,
never user-supplied names:

    workspaces/<ws>/projects/<proj>/documents/<doc>/source.pdf
    workspaces/<ws>/projects/<proj>/documents/<doc>/runs/<run>/...

Nothing here is reachable through the public /output mount; serving goes
through the membership-checked /api/files route (or presigned URLs on S3).
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from rk3.platform import config


def doc_dir_key(ws: uuid.UUID, proj: uuid.UUID | None, doc: uuid.UUID) -> str:
    proj_part = f"projects/{proj}/" if proj else ""
    return f"workspaces/{ws}/{proj_part}documents/{doc}"


def source_key(ws: uuid.UUID, proj: uuid.UUID | None, doc: uuid.UUID) -> str:
    return f"{doc_dir_key(ws, proj, doc)}/source.pdf"


def run_prefix(ws: uuid.UUID, proj: uuid.UUID | None, doc: uuid.UUID, run: uuid.UUID) -> str:
    return f"{doc_dir_key(ws, proj, doc)}/runs/{run}"


class LocalDiskStorage:
    """Private tree on this box. `path()` is local-only (FileResponse / worker
    access); an S3 adapter offers `presigned_url()` instead — the API layer
    picks whichever the backend provides."""

    def __init__(self, root: Path | None = None):
        self.root = Path(root or config.STORAGE_ROOT)

    def path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise ValueError("storage key escapes the root")
        return p

    def save_bytes(self, key: str, data: bytes) -> int:
        p = self.path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return len(data)

    def save_stream(self, key: str, stream) -> int:
        p = self.path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("wb") as out:
            shutil.copyfileobj(stream, out)
        return p.stat().st_size

    def exists(self, key: str) -> bool:
        return self.path(key).exists()

    def delete_prefix(self, prefix: str) -> None:
        p = self.path(prefix)
        if p.is_dir():
            shutil.rmtree(p)


def get_storage() -> LocalDiskStorage:
    return LocalDiskStorage()
