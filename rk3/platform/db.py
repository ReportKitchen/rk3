"""Engine + session plumbing. One engine per process; FastAPI gets a
per-request session via `get_db`, the worker uses `session_scope`."""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from rk3.platform import config

_engine = None
_Session: sessionmaker | None = None


def engine():
    global _engine, _Session
    if _engine is None:
        if not config.DATABASE_URL:
            raise RuntimeError("RK3_DATABASE_URL is not configured (.env)")
        _engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_db():
    """FastAPI dependency: one session per request."""
    engine()
    db = _Session()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """Worker/seed helper: commit on success, rollback on error."""
    engine()
    db = _Session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
