"""Entitlements: which products/limits the WORKSPACE has obtained. Separate
from roles on purpose — an editor may have permission to use LPM while the
workspace lacks the entitlement, and vice versa (plan rule).

Effective features = the union of all currently-valid grants (whole plans
expand to their plan_entitlements; direct feature grants apply as-is). For
numeric features the most generous valid limit wins; None = unlimited."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from rk3.platform.models import EntitlementGrant, PlanEntitlement

# feature keys (Stage 1 — LPM). Numbers live in the DB catalog, not here.
LPM_ACCESS = "lpm.access"
LPM_PROJECTS_MAX = "lpm.projects.max"
LPM_DOCUMENTS_MAX = "lpm.documents.max"
LPM_UPLOAD_MB_MAX = "lpm.upload_mb.max"
LPM_PAGES_MAX = "lpm.pages.max"
LPM_AI_MONTHLY = "lpm.ai_generations.monthly"
RK_EXPRESS_ACCESS = "rk_express.access"


def workspace_features(db: Session, workspace_id: uuid.UUID) -> dict[str, int | None]:
    """{feature: limit} for every feature the workspace currently holds.
    limit None means enabled without a numeric cap."""
    now = datetime.now(timezone.utc)
    grants = db.execute(
        select(EntitlementGrant).where(
            EntitlementGrant.workspace_id == workspace_id,
            EntitlementGrant.valid_from <= now,
        )
    ).scalars().all()
    out: dict[str, int | None] = {}

    def add(feature: str, limit: int | None) -> None:
        if feature not in out:
            out[feature] = limit
        elif out[feature] is not None and (limit is None or limit > out[feature]):
            out[feature] = limit  # most generous valid grant wins

    for g in grants:
        if g.valid_until is not None and g.valid_until <= now:
            continue
        if g.feature:
            add(g.feature, g.limit_int)
        if g.plan_key:
            rows = db.execute(
                select(PlanEntitlement).where(PlanEntitlement.plan_key == g.plan_key)
            ).scalars().all()
            for r in rows:
                add(r.feature, r.limit_int)
    return out


def require_feature(db: Session, workspace_id: uuid.UUID, feature: str) -> int | None:
    """The workspace must hold the feature; returns its limit (None = no cap)."""
    feats = workspace_features(db, workspace_id)
    if feature not in feats:
        raise HTTPException(403, f"this workspace has no {feature} entitlement")
    return feats[feature]


def require_quota(db: Session, workspace_id: uuid.UUID, feature: str,
                  current_count: int) -> None:
    """For numeric features: current usage must sit under the limit."""
    limit = require_feature(db, workspace_id, feature)
    if limit is not None and current_count >= limit:
        raise HTTPException(403, f"{feature} limit reached ({limit})")
