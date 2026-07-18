"""Idempotent bootstrap: product catalog, the internal workspace (today's
corpus becomes staff-only tenant data — plan Stage 4 pulled forward), and the
dev identity for this box. Run: python -m rk3.platform.seed"""
from __future__ import annotations

from sqlalchemy import select

from rk3.documents import list_documents
from rk3.platform import config
from rk3.platform.db import session_scope
from rk3.platform.models import (Document, EntitlementGrant, Membership, Plan,
                                 PlanEntitlement, Tool, User, Workspace)

# Placeholder free-tier numbers — the real limits are the owner's decision #5
# (see the execution plan). Change the DB rows, not code.
LPM_FREE_FEATURES = [
    ("lpm.access", None),
    ("lpm.projects.max", 3),
    ("lpm.documents.max", 5),
    ("lpm.upload_mb.max", 50),
    ("lpm.pages.max", 150),
    ("lpm.ai_generations.monthly", 20),
]


def seed() -> dict:
    out = {"created": []}
    with session_scope() as db:
        # ---- catalog ----
        for key, name in [("lpm", "Landing Page Maker"), ("rk_express", "RK Express")]:
            if db.get(Tool, key) is None:
                db.add(Tool(key=key, name=name))
                out["created"].append(f"tool:{key}")
        if db.get(Plan, "lpm_free") is None:
            db.add(Plan(key="lpm_free", name="Landing Page Maker (free)"))
            out["created"].append("plan:lpm_free")
        for feature, limit in LPM_FREE_FEATURES:
            exists = db.execute(select(PlanEntitlement).where(
                PlanEntitlement.plan_key == "lpm_free",
                PlanEntitlement.feature == feature)).scalar_one_or_none()
            if exists is None:
                db.add(PlanEntitlement(plan_key="lpm_free", feature=feature, limit_int=limit))
                out["created"].append(f"feature:{feature}")

        # ---- dev identity (this box; AUTH_MODE=dev logs in as this user) ----
        dev = db.execute(select(User).where(
            User.identity_subject == config.DEV_USER_SUBJECT)).scalar_one_or_none()
        if dev is None:
            dev = User(identity_subject=config.DEV_USER_SUBJECT,
                       email=config.DEV_USER_EMAIL, display_name="Dev Owner",
                       platform_role="platform_admin")
            db.add(dev)
            db.flush()
            out["created"].append("user:dev")

        # ---- the internal workspace holding today's corpus ----
        internal = db.execute(select(Workspace).where(
            Workspace.type == "internal")).scalar_one_or_none()
        if internal is None:
            internal = Workspace(name="Report Kitchen (internal)", type="internal")
            db.add(internal)
            db.flush()
            db.add(Membership(workspace_id=internal.id, user_id=dev.id, role="owner"))
            # staff surface: unrestricted tool access via an admin grant
            db.add(EntitlementGrant(workspace_id=internal.id, feature="lpm.access",
                                    source="admin_grant", reason="internal workspace"))
            db.add(EntitlementGrant(workspace_id=internal.id, feature="rk_express.access",
                                    source="admin_grant", reason="internal workspace"))
            out["created"].append("workspace:internal")

        # ---- dev user's personal workspace with the free plan (the signup shape) ----
        personal = db.execute(select(Workspace).where(
            Workspace.type == "personal")).scalar_one_or_none()
        if personal is None:
            personal = Workspace(name="Dev Owner", type="personal")
            db.add(personal)
            db.flush()
            db.add(Membership(workspace_id=personal.id, user_id=dev.id, role="owner"))
            db.add(EntitlementGrant(workspace_id=personal.id, plan_key="lpm_free",
                                    source="free_plan", reason="signup default"))
            out["created"].append("workspace:personal")

        # ---- corpus import: existing sources/ docs -> legacy document rows ----
        have = {s for (s,) in db.execute(select(Document.slug).where(Document.legacy))}
        added = 0
        for d in list_documents():
            if d["slug"] in have:
                continue
            db.add(Document(workspace_id=internal.id, name=d["name"], legacy=True,
                            slug=d["slug"],
                            status="converted" if d.get("status") == "done" else "uploaded"))
            added += 1
        if added:
            out["created"].append(f"documents:{added} legacy")
    return out


if __name__ == "__main__":
    print(seed())
