"""Append-only audit log for security/business changes (not analytics, not
operational logging — those stay separate per the plan)."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from rk3.platform.models import AuditEvent


def record(db: Session, action: str, *, actor: uuid.UUID | None = None,
           workspace: uuid.UUID | None = None, target_type: str = "",
           target_id: str = "", request_id: str = "", reason: str = "",
           data: dict | None = None) -> None:
    db.add(AuditEvent(
        action=action, actor_user_id=actor, workspace_id=workspace,
        target_type=target_type, target_id=str(target_id or ""),
        request_id=request_id, reason=reason, data=data or {},
    ))
