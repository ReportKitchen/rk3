"""The platform schema — PostgreSQL as the source of truth.

Follows the owner's plan (docs/DEFERRED/multi-user-platform-plan.md): tenant =
`workspace` (every signup gets a personal one), roles live on `memberships`,
products/limits live in the plans/entitlements catalog, jobs are durable rows,
audit is append-only. UUID keys everywhere; no user-supplied identifiers in
storage paths.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (BigInteger, Boolean, DateTime, ForeignKey, Index,
                        Integer, String, Text, UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


UUIDpk = UUID(as_uuid=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    identity_subject: Mapped[str] = mapped_column(String(255), unique=True)  # OIDC sub (or dev:*)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    # platform-level (staff) role — workspace roles live on memberships
    platform_role: Mapped[str] = mapped_column(String(32), default="member")  # member|platform_admin|support
    status: Mapped[str] = mapped_column(String(32), default="active")  # active|suspended
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(32), default="personal")  # personal|team|internal
    status: Mapped[str] = mapped_column(String(32), default="active")  # active|suspended
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)  # e.g. {"aiLevel": "full"}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="workspace")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(32))  # owner|billing_admin|admin|editor|viewer
    status: Mapped[str] = mapped_column(String(32), default="active")  # active|removed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    workspace: Mapped[Workspace] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class Invitation(Base):
    __tablename__ = "invitations"
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(32), default="editor")
    token_hash: Mapped[str] = mapped_column(String(128))          # sha256; raw token only in the email
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---- product catalog: tools, plans, entitlements ---------------------------

class Tool(Base):
    __tablename__ = "tools"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)  # lpm | rk_express
    name: Mapped[str] = mapped_column(String(200))


class Plan(Base):
    __tablename__ = "plans"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)  # lpm_free | lpm_pro | ...
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="active")


class PlanEntitlement(Base):
    """One feature a plan grants. Presence = enabled; `limit_int` carries a
    quota when the feature is numeric (lpm.projects.max = 3)."""
    __tablename__ = "plan_entitlements"
    __table_args__ = (UniqueConstraint("plan_key", "feature"),)
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    plan_key: Mapped[str] = mapped_column(ForeignKey("plans.key", ondelete="CASCADE"))
    feature: Mapped[str] = mapped_column(String(120))  # e.g. lpm.access, lpm.projects.max
    limit_int: Mapped[int | None] = mapped_column(Integer, nullable=True)


class EntitlementGrant(Base):
    """What a workspace has obtained: a whole plan, or one direct feature.
    Same shape covers free plans, trials, admin grants, and (later) Stripe
    subscription projections — `source` + `provider_reference` say which."""
    __tablename__ = "entitlement_grants"
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    plan_key: Mapped[str | None] = mapped_column(ForeignKey("plans.key"), nullable=True)
    feature: Mapped[str | None] = mapped_column(String(120), nullable=True)
    limit_int: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(32))  # free_plan|subscription|trial|discount|admin_grant
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    provider_reference: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---- projects, documents, runs, artifacts ----------------------------------

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    tool_key: Mapped[str] = mapped_column(ForeignKey("tools.key"))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="active")  # active|archived
    version: Mapped[int] = mapped_column(Integer, default=0)  # optimistic concurrency on state saves
    state: Mapped[dict] = mapped_column(JSONB, default=dict)  # LPM assembled state (migrating off sidecars)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(300))                  # original filename
    # legacy corpus docs keep living under sources/ and are addressed by slug;
    # uploaded docs live in private storage under storage_key
    legacy: Mapped[bool] = mapped_column(Boolean, default=False)
    slug: Mapped[str | None] = mapped_column(String(300), unique=True, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded")  # uploaded|processing|converted|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Run(Base):
    """One conversion of one document — outputs live under its storage prefix."""
    __tablename__ = "runs"
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), default="queued")  # queued|running|succeeded|failed
    storage_prefix: Mapped[str] = mapped_column(String(500), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(32), default="other")  # ir|html|page|image|log|export|other
    rel_path: Mapped[str] = mapped_column(String(500))              # relative to the run's storage prefix
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---- durable jobs ----------------------------------------------------------

class Job(Base):
    """Durable truth for background work — replaces process-memory sets. The
    worker claims with FOR UPDATE SKIP LOCKED; retries re-queue with backoff."""
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_claim", "status", "run_after"),)
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    kind: Mapped[str] = mapped_column(String(64))                   # convert | ...
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="queued")  # queued|running|succeeded|failed|cancelled
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    claimed_by: Mapped[str] = mapped_column(String(128), default="")
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---- sessions + audit ------------------------------------------------------

class SessionRecord(Base):
    """Server-side login sessions (revocable, listable) — the browser holds
    only a signed opaque id in an HttpOnly cookie."""
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(300), default="")


class AuditEvent(Base):
    """Append-only. Security/business changes only — not analytics, not ops."""
    __tablename__ = "audit_events"
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=_uuid)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120))                # e.g. auth.login, project.create
    target_type: Mapped[str] = mapped_column(String(64), default="")
    target_id: Mapped[str] = mapped_column(String(64), default="")
    request_id: Mapped[str] = mapped_column(String(64), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
