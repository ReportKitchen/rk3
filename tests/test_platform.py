"""Platform foundation tests: permission matrix, entitlement resolution,
durable-job lifecycle, sessions/CSRF, and the upload flow. Runs against the
rk3_test database (schema recreated per test session)."""
import io
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("RK3_TEST", "1")

from rk3.platform import config  # noqa: E402

# point the platform at the test database BEFORE any engine is created
config.DATABASE_URL = config.DATABASE_URL.rsplit("/", 1)[0] + "/rk3_test"
config.AUTH_MODE = "dev"

from rk3.platform import db as dbmod  # noqa: E402
from rk3.platform import entitlements, jobs, permissions  # noqa: E402
from rk3.platform.auth import csrf_token_for  # noqa: E402
from rk3.platform.models import (Base, EntitlementGrant, Membership, Plan,  # noqa: E402
                                 PlanEntitlement, Tool, User, Workspace)

from fastapi import HTTPException  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    eng = dbmod.engine()
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def db(engine):
    s = dbmod._Session()
    yield s
    s.rollback()
    s.close()


def _user(db, subject=None, role="member"):
    u = User(identity_subject=subject or f"t:{uuid.uuid4()}",
             email=f"{uuid.uuid4()}@t.local", platform_role=role)
    db.add(u)
    db.flush()
    return u


def _workspace(db, user, role="owner"):
    w = Workspace(name="W", type="personal")
    db.add(w)
    db.flush()
    db.add(Membership(workspace_id=w.id, user_id=user.id, role=role))
    db.flush()
    return w


# ---------------------------------------------------------------- permissions

def test_permission_matrix_shape():
    P = permissions
    assert P.PROJECT_CREATE in P.permissions_for("owner")
    assert P.PROJECT_CREATE in P.permissions_for("editor")
    assert P.PROJECT_CREATE not in P.permissions_for("viewer")
    assert P.BILLING_MANAGE in P.permissions_for("owner")
    assert P.BILLING_MANAGE in P.permissions_for("billing_admin")
    assert P.BILLING_MANAGE not in P.permissions_for("admin")
    assert P.MEMBERS_MANAGE in P.permissions_for("admin")
    assert P.MEMBERS_MANAGE not in P.permissions_for("editor")
    assert P.PROJECT_VIEW in P.permissions_for("viewer")
    assert P.permissions_for("nonsense") == frozenset()


def test_membership_scoping(db):
    alice, bob = _user(db), _user(db)
    ws = _workspace(db, alice, role="owner")
    # member passes
    m = permissions.require_member(db, alice, ws.id, permissions.PROJECT_CREATE)
    assert m.role == "owner"
    # non-member gets 404 (existence not confirmed), not 403
    with pytest.raises(HTTPException) as e:
        permissions.require_member(db, bob, ws.id, permissions.PROJECT_VIEW)
    assert e.value.status_code == 404
    # role without the permission gets 403
    db.add(Membership(workspace_id=ws.id, user_id=bob.id, role="viewer"))
    db.flush()
    with pytest.raises(HTTPException) as e:
        permissions.require_member(db, bob, ws.id, permissions.PROJECT_CREATE)
    assert e.value.status_code == 403


def test_platform_admin_passes_without_membership(db):
    staff = _user(db, role="platform_admin")
    ws = _workspace(db, _user(db))
    m = permissions.require_member(db, staff, ws.id, permissions.PROJECT_VIEW)
    assert m is not None


# --------------------------------------------------------------- entitlements

def _catalog(db):
    if db.get(Tool, "lpm") is None:
        db.add(Tool(key="lpm", name="LPM"))
    if db.get(Plan, "lpm_free") is None:
        db.add(Plan(key="lpm_free", name="free"))
        db.add(PlanEntitlement(plan_key="lpm_free", feature="lpm.access"))
        db.add(PlanEntitlement(plan_key="lpm_free", feature="lpm.projects.max", limit_int=3))
    db.flush()


def test_plan_grant_expands_to_features(db):
    _catalog(db)
    ws = _workspace(db, _user(db))
    db.add(EntitlementGrant(workspace_id=ws.id, plan_key="lpm_free", source="free_plan"))
    db.flush()
    feats = entitlements.workspace_features(db, ws.id)
    assert feats["lpm.access"] is None
    assert feats["lpm.projects.max"] == 3


def test_expired_grant_is_ignored(db):
    _catalog(db)
    ws = _workspace(db, _user(db))
    db.add(EntitlementGrant(workspace_id=ws.id, plan_key="lpm_free", source="trial",
                            valid_until=datetime.now(timezone.utc) - timedelta(days=1)))
    db.flush()
    assert entitlements.workspace_features(db, ws.id) == {}
    with pytest.raises(HTTPException) as e:
        entitlements.require_feature(db, ws.id, "lpm.access")
    assert e.value.status_code == 403


def test_most_generous_grant_wins(db):
    _catalog(db)
    ws = _workspace(db, _user(db))
    db.add(EntitlementGrant(workspace_id=ws.id, plan_key="lpm_free", source="free_plan"))
    db.add(EntitlementGrant(workspace_id=ws.id, feature="lpm.projects.max",
                            limit_int=10, source="admin_grant", reason="support bump"))
    db.flush()
    assert entitlements.workspace_features(db, ws.id)["lpm.projects.max"] == 10
    entitlements.require_quota(db, ws.id, "lpm.projects.max", 9)      # under
    with pytest.raises(HTTPException):
        entitlements.require_quota(db, ws.id, "lpm.projects.max", 10)  # at limit


# ----------------------------------------------------------------------- jobs

def test_job_lifecycle_claim_retry_dead(db):
    j = jobs.enqueue(db, "convert", {"x": 1}, max_attempts=2)
    db.commit()
    claimed = jobs.claim_one(db, "w1")
    assert claimed is not None and claimed.id == j.id
    assert claimed.status == "running" and claimed.attempts == 1
    # nothing else to claim while running
    assert jobs.claim_one(db, "w2") is None
    # failure 1 -> requeued with backoff
    jobs.finish(db, claimed, error="boom")
    assert claimed.status == "queued" and claimed.error == "boom"
    assert claimed.run_after > datetime.now(timezone.utc)
    # make it runnable now, fail again -> dead
    claimed.run_after = datetime.now(timezone.utc)
    db.commit()
    again = jobs.claim_one(db, "w1")
    assert again is not None and again.attempts == 2
    jobs.finish(db, again, error="boom2")
    assert again.status == "failed" and again.finished_at is not None


def test_job_success_path(db):
    j = jobs.enqueue(db, "convert", {})
    db.commit()
    c = jobs.claim_one(db, "w")
    jobs.finish(db, c)
    assert c.status == "succeeded" and c.error == ""


# ------------------------------------------------------------- sessions / API

@pytest.fixture(scope="session")
def client(engine):
    from fastapi.testclient import TestClient
    from app.main import app
    from rk3.platform.seed import seed
    seed()
    return TestClient(app)


def test_me_anonymous(client):
    r = client.get("/api/me")
    assert r.status_code == 200
    assert r.json()["user"] is None


def test_dev_login_and_csrf_flow(client):
    r = client.post("/api/auth/dev-login")
    assert r.status_code == 200
    me = client.get("/api/me").json()
    assert me["user"]["email"] and me["workspaces"]
    personal = next(w for w in me["workspaces"] if w["type"] == "personal")

    # without CSRF: rejected
    r = client.post(f"/api/platform/workspaces/{personal['id']}/projects",
                    json={"name": "x"})
    assert r.status_code == 403

    csrf = client.cookies.get(config.CSRF_COOKIE)
    r = client.post(f"/api/platform/workspaces/{personal['id']}/projects",
                    json={"name": "Test project"},
                    headers={"x-csrf-token": csrf})
    assert r.status_code == 201, r.text

    # non-pdf upload rejected
    pid = r.json()["id"]
    r = client.post(f"/api/platform/projects/{pid}/documents",
                    files={"file": ("x.txt", io.BytesIO(b"hi"), "text/plain")},
                    headers={"x-csrf-token": csrf})
    assert r.status_code == 400

    # pdf accepted -> document + queued job
    r = client.post(f"/api/platform/projects/{pid}/documents",
                    files={"file": ("t.pdf", io.BytesIO(b"%PDF-1.4 tiny"), "application/pdf")},
                    headers={"x-csrf-token": csrf})
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["job"]["status"] == "queued"

    # logout kills the session
    r = client.post("/api/auth/logout")
    assert r.status_code == 200
    assert client.get("/api/me").json()["user"] is None


def test_project_quota_enforced(client):
    client.post("/api/auth/dev-login")
    me = client.get("/api/me").json()
    personal = next(w for w in me["workspaces"] if w["type"] == "personal")
    csrf = client.cookies.get(config.CSRF_COOKIE)
    # lpm_free seeds projects.max = 3; one exists from the previous test
    made, last = 0, None
    for i in range(4):
        last = client.post(f"/api/platform/workspaces/{personal['id']}/projects",
                           json={"name": f"p{i}"}, headers={"x-csrf-token": csrf})
        if last.status_code == 201:
            made += 1
    assert made == 2                     # 1 existing + 2 new = 3 (the cap)
    assert last.status_code == 403
    assert "limit" in last.json()["detail"]


def test_project_state_optimistic_concurrency(client):
    client.post("/api/auth/dev-login")
    me = client.get("/api/me").json()
    personal = next(w for w in me["workspaces"] if w["type"] == "personal")
    csrf = client.cookies.get(config.CSRF_COOKIE)
    pid = client.get(f"/api/platform/workspaces/{personal['id']}/projects").json()[0]["id"]

    s = client.get(f"/api/platform/projects/{pid}/state").json()
    assert s["version"] == 0 and s["state"] == {}
    r = client.put(f"/api/platform/projects/{pid}/state",
                   json={"state": {"a": 1}, "version": 0},
                   headers={"x-csrf-token": csrf})
    assert r.status_code == 200 and r.json()["version"] == 1
    # a second writer holding version 0 conflicts
    r = client.put(f"/api/platform/projects/{pid}/state",
                   json={"state": {"b": 2}, "version": 0},
                   headers={"x-csrf-token": csrf})
    assert r.status_code == 409
    assert client.get(f"/api/platform/projects/{pid}/state").json()["state"] == {"a": 1}


def test_admin_surface_staff_only(client, db):
    client.post("/api/auth/dev-login")
    assert client.get("/api/platform/admin/overview").status_code == 200
    audit_rows = client.get("/api/platform/admin/audit").json()
    assert any(e["action"] == "auth.login" for e in audit_rows)
    # a plain member sees nothing (404, surface unadvertised)
    from sqlalchemy import select as _sel
    u = db.execute(_sel(User).where(
        User.identity_subject == config.DEV_USER_SUBJECT)).scalar_one()
    u.platform_role = "member"
    db.commit()
    assert client.get("/api/platform/admin/overview").status_code == 404
    u.platform_role = "platform_admin"
    db.commit()


def test_staff_gate_on_legacy_api(client, db):
    """The corpus/staff surface must not be world- or member-readable."""
    client.post("/api/auth/logout")
    assert client.get("/api/documents").status_code == 401       # anonymous
    assert client.get("/api/me").status_code == 200              # platform: open
    client.post("/api/auth/dev-login")
    assert client.get("/api/documents").status_code == 200       # staff
    from sqlalchemy import select as _sel
    u = db.execute(_sel(User).where(
        User.identity_subject == config.DEV_USER_SUBJECT)).scalar_one()
    u.platform_role = "member"
    db.commit()
    assert client.get("/api/documents").status_code == 403       # plain member
    u.platform_role = "platform_admin"
    db.commit()


def test_cross_workspace_isolation(client, db):
    """A signed-in user must not see another workspace's documents (404)."""
    client.post("/api/auth/dev-login")
    other_owner = _user(db)
    other_ws = _workspace(db, other_owner)
    from rk3.platform.models import Document
    d = Document(workspace_id=other_ws.id, name="secret.pdf")
    db.add(d)
    db.commit()
    r = client.get(f"/api/platform/documents/{d.id}")
    # dev user is platform_admin (staff can see); simulate a plain member
    u = db.execute(
        __import__("sqlalchemy").select(User).where(
            User.identity_subject == config.DEV_USER_SUBJECT)).scalar_one()
    u.platform_role = "member"
    db.commit()
    r = client.get(f"/api/platform/documents/{d.id}")
    assert r.status_code == 404
    u.platform_role = "platform_admin"
    db.commit()
