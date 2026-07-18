"""Centralized authorization: roles translate to permissions HERE, nowhere
else — no `if role == "owner"` scattered through endpoints (plan rule). Every
resource access scopes through the authorized workspace; a bare UUID existing
is never enough."""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from rk3.platform.models import Membership, User, Workspace

# the permission vocabulary (grow per tool; keep namespaced)
WORKSPACE_VIEW = "workspace.view"
MEMBERS_INVITE = "workspace.members.invite"
MEMBERS_MANAGE = "workspace.members.manage"
BILLING_MANAGE = "workspace.billing.manage"
WORKSPACE_ADMIN = "workspace.settings.manage"
PROJECT_CREATE = "project.create"
PROJECT_EDIT = "project.edit"
PROJECT_VIEW = "project.view"
PROJECT_EXPORT = "project.export"

_VIEWER = {WORKSPACE_VIEW, PROJECT_VIEW, PROJECT_EXPORT}
_EDITOR = _VIEWER | {PROJECT_CREATE, PROJECT_EDIT}
_ADMIN = _EDITOR | {MEMBERS_INVITE, MEMBERS_MANAGE, WORKSPACE_ADMIN}
_BILLING = _VIEWER | {BILLING_MANAGE}
_OWNER = _ADMIN | _BILLING

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "owner": frozenset(_OWNER),
    "billing_admin": frozenset(_BILLING),
    "admin": frozenset(_ADMIN),
    "editor": frozenset(_EDITOR),
    "viewer": frozenset(_VIEWER),
}


def permissions_for(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def membership_for(db: Session, user: User, workspace_id: uuid.UUID) -> Membership | None:
    return db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == user.id,
            Membership.status == "active",
        )
    ).scalar_one_or_none()


def require_member(db: Session, user: User, workspace_id: uuid.UUID,
                   permission: str) -> Membership:
    """The one gate: active membership in THIS workspace whose role carries the
    permission. Platform admins pass (staff surface), but the act is auditable
    by the caller. 404 (not 403) for non-members — don't confirm existence."""
    ws = db.get(Workspace, workspace_id)
    if ws is None or ws.status != "active":
        raise HTTPException(404, "unknown workspace")
    m = membership_for(db, user, workspace_id)
    if m is None:
        if user.platform_role == "platform_admin":
            return Membership(workspace_id=workspace_id, user_id=user.id, role="owner")
        raise HTTPException(404, "unknown workspace")
    if permission not in permissions_for(m.role):
        raise HTTPException(403, "not permitted")
    return m
