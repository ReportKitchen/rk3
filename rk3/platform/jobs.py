"""Durable jobs: the PostgreSQL row is the truth (survives restarts — the
process-memory sets don't). Claiming uses FOR UPDATE SKIP LOCKED so several
workers can run safely; failures re-queue with backoff up to max_attempts."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from rk3.platform.models import Job


def enqueue(db: Session, kind: str, payload: dict,
            workspace_id: uuid.UUID | None = None, max_attempts: int = 3) -> Job:
    job = Job(kind=kind, payload=payload, workspace_id=workspace_id,
              max_attempts=max_attempts)
    db.add(job)
    db.flush()
    return job


def claim_one(db: Session, worker_name: str) -> Job | None:
    """Atomically claim the oldest runnable job (skipping ones other workers
    hold). Commit happens here so the claim is visible immediately."""
    now = datetime.now(timezone.utc)
    job = db.execute(
        select(Job)
        .where(Job.status == "queued", Job.run_after <= now)
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).scalar_one_or_none()
    if job is None:
        return None
    job.status = "running"
    job.attempts += 1
    job.claimed_by = worker_name
    job.heartbeat_at = now
    db.commit()
    return job


def heartbeat(db: Session, job: Job) -> None:
    job.heartbeat_at = datetime.now(timezone.utc)
    db.commit()


def finish(db: Session, job: Job, *, error: str = "") -> None:
    """Success, or failure with retry-then-dead semantics."""
    now = datetime.now(timezone.utc)
    if not error:
        job.status = "succeeded"
        job.error = ""
        job.finished_at = now
    elif job.attempts < job.max_attempts:
        job.status = "queued"                      # retry with backoff
        job.error = error
        job.run_after = now + timedelta(seconds=30 * (2 ** (job.attempts - 1)))
    else:
        job.status = "failed"
        job.error = error
        job.finished_at = now
    db.commit()


def cancel(db: Session, job: Job) -> bool:
    if job.status in ("queued",):
        job.status = "cancelled"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        return True
    return False
