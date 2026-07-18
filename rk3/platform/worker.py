"""The dedicated worker: claims durable jobs and runs them out-of-process.

Run: python -m rk3.platform.worker   (systemd: rk3-worker.service)

Conversion executes as a subprocess (`python -m rk3 convert-path`) exactly like
the existing app spawns corpus conversions — crash/OOM isolation and a log the
job row can point at. Public-launch container isolation for untrusted PDFs is
parked (see the execution plan); the resource story here matches the current
app's.
"""
from __future__ import annotations

import logging
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rk3.platform import config
from rk3.platform.db import session_scope
from rk3.platform.jobs import claim_one, finish
from rk3.platform.models import Artifact, Document, Job, Run
from rk3.platform.storage import get_storage

log = logging.getLogger("rk3.worker")
ROOT = Path(__file__).resolve().parent.parent.parent

ARTIFACT_KINDS = {
    ".json": "ir", ".html": "html", ".png": "image", ".jpg": "image",
    ".svg": "image", ".log": "log", ".txt": "log", ".css": "other",
}


def _kind(path: Path) -> str:
    if path.name == "ir.json":
        return "ir"
    return ARTIFACT_KINDS.get(path.suffix.lower(), "other")


def handle_convert(db, job: Job) -> None:
    """payload: {document_id, run_id} — convert the uploaded source into the
    run's private storage prefix and register every produced file."""
    storage = get_storage()
    doc = db.get(Document, uuid.UUID(job.payload["document_id"]))
    run = db.get(Run, uuid.UUID(job.payload["run_id"]))
    if doc is None or run is None:
        raise RuntimeError("job references a missing document/run")

    src = storage.path(doc.storage_key)
    outdir = storage.path(run.storage_prefix)
    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    doc.status = "processing"
    db.commit()

    cmd = [sys.executable, "-m", "rk3", "convert-path", str(src), str(outdir)]
    r = subprocess.run(cmd, cwd=ROOT, timeout=config.CONVERT_TIMEOUT_SECONDS,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (outdir / "convert.log").write_text(
        f"$ {' '.join(cmd)}\nexit={r.returncode}\n\n{r.stdout or ''}")

    ok = r.returncode == 0
    if ok:
        count = 0
        for p in sorted(outdir.rglob("*")):
            if not p.is_file():
                continue
            db.add(Artifact(run_id=run.id, kind=_kind(p),
                            rel_path=str(p.relative_to(outdir)),
                            size_bytes=p.stat().st_size))
            count += 1
        # page count from the produced IR
        try:
            import json
            ir = json.loads((outdir / "ir.json").read_text())
            if isinstance(ir.get("pages"), list):
                doc.pages = len(ir["pages"])
        except Exception:
            pass
        run.status = "succeeded"
        doc.status = "converted"
        log.info("convert ok: doc=%s run=%s artifacts=%d", doc.id, run.id, count)
    else:
        run.status = "failed"
        run.error = (r.stdout or "")[-2000:]
        doc.status = "failed"
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    if not ok:
        raise RuntimeError(f"convert exited {r.returncode}")


HANDLERS = {"convert": handle_convert}


def run_worker() -> None:
    name = f"{socket.gethostname()}:{uuid.uuid4().hex[:6]}"
    log.info("worker %s starting (poll %.1fs)", name, config.WORKER_POLL_SECONDS)
    while True:
        try:
            with session_scope() as db:
                job = claim_one(db, name)
                if job is None:
                    db.commit()
                    time.sleep(config.WORKER_POLL_SECONDS)
                    continue
                log.info("claimed %s job %s (attempt %d)", job.kind, job.id, job.attempts)
                handler = HANDLERS.get(job.kind)
                try:
                    if handler is None:
                        raise RuntimeError(f"no handler for job kind {job.kind!r}")
                    handler(db, job)
                    finish(db, job)
                except Exception as e:  # job-level failure -> retry/dead, keep looping
                    log.warning("job %s failed: %s", job.id, e)
                    finish(db, job, error=f"{type(e).__name__}: {e}"[:2000])
        except KeyboardInterrupt:
            log.info("worker stopping")
            return
        except Exception:  # infrastructure hiccup (db restart etc.) — back off, survive
            log.exception("worker loop error")
            time.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    run_worker()
