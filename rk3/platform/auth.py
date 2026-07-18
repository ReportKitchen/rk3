"""Sessions + the backend-for-frontend contract.

The browser holds ONE HttpOnly cookie: a signed, opaque session id. The
session row lives in the DB (listable, revocable — an admin requirement).
OIDC tokens never reach the browser (oidc.py keeps the exchange server-side);
in dev mode an explicit /api/auth/dev-login stands in for the provider.

CSRF: double-submit. A non-HttpOnly cookie carries a token deterministically
derived from the session id (no extra storage); state-changing platform routes
require the X-CSRF-Token header to match.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.orm import Session

from rk3.platform import config
from rk3.platform.models import SessionRecord, User


def _serializer() -> URLSafeSerializer:
    if not config.SESSION_SECRET:
        raise RuntimeError("RK3_SESSION_SECRET is not configured (.env)")
    return URLSafeSerializer(config.SESSION_SECRET, salt="rk3-session")


def csrf_token_for(session_id: uuid.UUID) -> str:
    return hmac.new(config.SESSION_SECRET.encode(), f"csrf:{session_id}".encode(),
                    hashlib.sha256).hexdigest()


def start_session(db: Session, user: User, request: Request, response: Response) -> SessionRecord:
    rec = SessionRecord(
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=config.SESSION_TTL_DAYS),
        ip=(request.client.host if request.client else "")[:64],
        user_agent=(request.headers.get("user-agent") or "")[:300],
    )
    db.add(rec)
    db.flush()
    signed = _serializer().dumps(str(rec.id))
    secure = request.url.scheme == "https"
    response.set_cookie(config.SESSION_COOKIE, signed, httponly=True,
                        samesite="lax", secure=secure,
                        max_age=config.SESSION_TTL_DAYS * 86400, path="/")
    response.set_cookie(config.CSRF_COOKIE, csrf_token_for(rec.id), httponly=False,
                        samesite="lax", secure=secure,
                        max_age=config.SESSION_TTL_DAYS * 86400, path="/")
    return rec


def end_session(db: Session, request: Request, response: Response) -> None:
    rec = _session_from_request(db, request)
    if rec is not None:
        rec.revoked_at = datetime.now(timezone.utc)
    response.delete_cookie(config.SESSION_COOKIE, path="/")
    response.delete_cookie(config.CSRF_COOKIE, path="/")


def _session_from_request(db: Session, request: Request) -> SessionRecord | None:
    raw = request.cookies.get(config.SESSION_COOKIE)
    if not raw:
        return None
    try:
        sid = _serializer().loads(raw)
    except BadSignature:
        return None
    rec = db.get(SessionRecord, uuid.UUID(sid))
    if rec is None or rec.revoked_at is not None:
        return None
    if rec.expires_at <= datetime.now(timezone.utc):
        return None
    return rec


def current_user(db: Session, request: Request) -> tuple[User, SessionRecord] | None:
    rec = _session_from_request(db, request)
    if rec is None:
        return None
    user = db.get(User, rec.user_id)
    if user is None or user.status != "active":
        return None
    return user, rec


def require_user(db: Session, request: Request) -> tuple[User, SessionRecord]:
    got = current_user(db, request)
    if got is None:
        raise HTTPException(401, "not signed in")
    return got


def require_csrf(request: Request, session: SessionRecord) -> None:
    """State-changing routes: header must match the session-derived token."""
    sent = request.headers.get(config.CSRF_HEADER, "")
    if not hmac.compare_digest(sent, csrf_token_for(session.id)):
        raise HTTPException(403, "missing or invalid CSRF token")
