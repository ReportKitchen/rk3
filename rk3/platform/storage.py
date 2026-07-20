"""Private file storage behind an adapter — LocalDiskStorage on this box,
S3Storage in production (RK3_STORAGE_BACKEND=s3). Keys follow the plan's
layout exactly and contain only generated UUIDs, never user-supplied names:

    workspaces/<ws>/projects/<proj>/documents/<doc>/source.pdf
    workspaces/<ws>/projects/<proj>/documents/<doc>/runs/<run>/...

Nothing here is reachable through the public /output mount. Serving goes
through the membership-checked /api/files route: local backend streams the
file, S3 backend redirects to a short-lived presigned URL (`url_for`).

The worker uses one backend-agnostic contract (the plan's worker shape):
`download_to` the source into a temp dir, convert, `upload_dir` the outputs.
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
    """Private tree on this box. `path()`/FileResponse serving; `url_for`
    returns None (no redirect needed)."""

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

    # ---- worker contract ----
    def download_to(self, key: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.path(key), dest)

    def upload_dir(self, local_dir: Path, prefix: str) -> list[tuple[str, int]]:
        """Store every file under local_dir at prefix/<relpath>. Returns
        [(relpath, size), ...]."""
        out = []
        for p in sorted(Path(local_dir).rglob("*")):
            if not p.is_file():
                continue
            rel = str(p.relative_to(local_dir))
            dest = self.path(f"{prefix}/{rel}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)
            out.append((rel, p.stat().st_size))
        return out

    # ---- serving ----
    def url_for(self, key: str, expires_seconds: int = 300) -> str | None:
        return None  # local: the API streams the file itself


class S3Storage:
    """Private S3 bucket. Same interface; serving hands out short-lived
    presigned URLs. Credentials/bucket come from config (.env)."""

    def __init__(self, bucket: str | None = None, region: str | None = None):
        import boto3
        self.bucket = bucket or config.S3_BUCKET
        if not self.bucket:
            raise RuntimeError("RK3_S3_BUCKET is not configured")
        self.client = boto3.client(
            "s3", region_name=region or config.S3_REGION,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY)

    def save_bytes(self, key: str, data: bytes) -> int:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return len(data)

    def save_stream(self, key: str, stream) -> int:
        self.client.upload_fileobj(stream, self.bucket, key)
        head = self.client.head_object(Bucket=self.bucket, Key=key)
        return int(head["ContentLength"])

    def exists(self, key: str) -> bool:
        import botocore
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except botocore.exceptions.ClientError:
            return False

    def delete_prefix(self, prefix: str) -> None:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix.rstrip("/") + "/"):
            objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if objs:
                self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": objs})

    # ---- worker contract ----
    def download_to(self, key: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, str(dest))

    def upload_dir(self, local_dir: Path, prefix: str) -> list[tuple[str, int]]:
        out = []
        for p in sorted(Path(local_dir).rglob("*")):
            if not p.is_file():
                continue
            rel = str(p.relative_to(local_dir))
            self.client.upload_file(str(p), self.bucket, f"{prefix}/{rel}")
            out.append((rel, p.stat().st_size))
        return out

    # ---- serving ----
    def url_for(self, key: str, expires_seconds: int = 300) -> str | None:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_seconds)


def get_storage():
    if config.STORAGE_BACKEND == "s3":
        return S3Storage()
    return LocalDiskStorage()
