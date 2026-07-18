"""Platform routes: auth (BFF), /api/me, workspaces, projects, uploads, jobs,
and membership-checked file serving. Additive — the existing internal routes
in main.py are untouched (they are the staff surface; tenantizing them is
Stage 4)."""
from __future__ import annotations

import uuid

from fastapi import (APIRouter, Depends, HTTPException, Request, Response,
                     UploadFile)
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rk3.platform import audit, config, entitlements, jobs, permissions
from rk3.platform.auth import (current_user, end_session, require_csrf,
                               require_user, start_session)
from rk3.platform.db import get_db
from rk3.platform.models import (Artifact, Document, Job, Membership, Project,
                                 Run, User, Workspace)
from rk3.platform.storage import get_storage, run_prefix, source_key

router = APIRouter()


# ---------------------------------------------------------------- auth (BFF)

@router.post("/api/auth/dev-login")
def dev_login(request: Request, response: Response, db: Session = Depends(get_db)):
    """This box only (RK3_AUTH_MODE=dev): sign in as the seeded dev owner.
    Explicit — never silent — so the session/cookie path is the same one
    production exercises."""
    if config.AUTH_MODE != "dev":
        raise HTTPException(404, "not found")
    dev = db.execute(select(User).where(
        User.identity_subject == config.DEV_USER_SUBJECT)).scalar_one_or_none()
    if dev is None:
        raise HTTPException(500, "dev user not seeded — run python -m rk3.platform.seed")
    start_session(db, dev, request, response)
    audit.record(db, "auth.login", actor=dev.id, data={"mode": "dev"})
    db.commit()
    return {"ok": True}


@router.get("/api/auth/login")
def oidc_login(request: Request, db: Session = Depends(get_db)):
    if config.AUTH_MODE != "oidc":
        raise HTTPException(404, "dev mode: use POST /api/auth/dev-login")
    from rk3.platform import oidc
    url, flow = oidc.begin_login()
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie(oidc.FLOW_COOKIE, flow, httponly=True, samesite="lax",
                    secure=request.url.scheme == "https", max_age=oidc.FLOW_TTL, path="/")
    return resp


@router.get("/api/auth/callback")
def oidc_callback(request: Request, code: str = "", state: str = "",
                  db: Session = Depends(get_db)):
    if config.AUTH_MODE != "oidc":
        raise HTTPException(404, "not found")
    from rk3.platform import oidc
    flow_cookie = request.cookies.get(oidc.FLOW_COOKIE, "")
    try:
        claims = oidc.finish_login(code, state, flow_cookie)
    except Exception as e:
        raise HTTPException(400, f"login failed: {e}") from e
    user = db.execute(select(User).where(
        User.identity_subject == claims["sub"])).scalar_one_or_none()
    if user is None:
        user = User(identity_subject=claims["sub"], email=claims["email"],
                    display_name=claims["name"])
        db.add(user)
        db.flush()
        # every signup gets a personal workspace with the free plan (plan rule)
        ws = Workspace(name=claims["name"] or claims["email"] or "Personal",
                       type="personal")
        db.add(ws)
        db.flush()
        db.add(Membership(workspace_id=ws.id, user_id=user.id, role="owner"))
        from rk3.platform.models import EntitlementGrant
        db.add(EntitlementGrant(workspace_id=ws.id, plan_key="lpm_free",
                                source="free_plan", reason="signup default"))
        audit.record(db, "user.signup", actor=user.id, workspace=ws.id)
    else:
        user.email = claims["email"] or user.email
        user.display_name = claims["name"] or user.display_name
    resp = RedirectResponse("/", status_code=302)
    start_session(db, user, request, resp)
    audit.record(db, "auth.login", actor=user.id, data={"mode": "oidc"})
    db.commit()
    resp.delete_cookie(oidc.FLOW_COOKIE, path="/")
    return resp


@router.post("/api/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    got = current_user(db, request)
    end_session(db, request, response)
    if got:
        audit.record(db, "auth.logout", actor=got[0].id)
    db.commit()
    return {"ok": True}


@router.get("/api/me")
def me(request: Request, db: Session = Depends(get_db)):
    """Session + workspace picture for the SPA boot. 200 always; user null when
    anonymous (the client decides whether to offer login)."""
    got = current_user(db, request)
    if got is None:
        return {"user": None, "workspaces": [], "authMode": config.AUTH_MODE}
    user, _ = got
    rows = db.execute(
        select(Membership, Workspace)
        .join(Workspace, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == user.id, Membership.status == "active",
               Workspace.status == "active")
    ).all()
    return {
        "user": {"id": str(user.id), "email": user.email,
                 "name": user.display_name, "platformRole": user.platform_role},
        "workspaces": [{"id": str(w.id), "name": w.name, "type": w.type,
                        "role": m.role} for m, w in rows],
        "authMode": config.AUTH_MODE,
    }


# ------------------------------------------------------------------ projects

def _auth(db: Session, request: Request):
    return require_user(db, request)


class ProjectIn(BaseModel):
    name: str
    tool_key: str = "lpm"


@router.get("/api/platform/workspaces/{ws_id}/projects")
def list_projects(ws_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    user, _ = _auth(db, request)
    permissions.require_member(db, user, ws_id, permissions.PROJECT_VIEW)
    rows = db.execute(select(Project).where(
        Project.workspace_id == ws_id, Project.status == "active")
        .order_by(Project.created_at.desc())).scalars().all()
    return [{"id": str(p.id), "name": p.name, "tool": p.tool_key,
             "createdAt": p.created_at.isoformat()} for p in rows]


@router.post("/api/platform/workspaces/{ws_id}/projects", status_code=201)
def create_project(ws_id: uuid.UUID, body: ProjectIn, request: Request,
                   db: Session = Depends(get_db)):
    user, sess = _auth(db, request)
    require_csrf(request, sess)
    permissions.require_member(db, user, ws_id, permissions.PROJECT_CREATE)
    entitlements.require_feature(db, ws_id, f"{body.tool_key}.access")
    count = db.execute(select(func.count()).select_from(Project).where(
        Project.workspace_id == ws_id, Project.status == "active",
        Project.tool_key == body.tool_key)).scalar_one()
    entitlements.require_quota(db, ws_id, f"{body.tool_key}.projects.max", count)
    p = Project(workspace_id=ws_id, tool_key=body.tool_key, name=body.name[:200])
    db.add(p)
    db.flush()
    audit.record(db, "project.create", actor=user.id, workspace=ws_id,
                 target_type="project", target_id=str(p.id))
    db.commit()
    return {"id": str(p.id), "name": p.name}


# ------------------------------------------------------- upload -> document/job

@router.post("/api/platform/projects/{project_id}/documents", status_code=202)
async def upload_document(project_id: uuid.UUID, file: UploadFile,
                          request: Request, db: Session = Depends(get_db)):
    user, sess = _auth(db, request)
    require_csrf(request, sess)
    project = db.get(Project, project_id)
    if project is None or project.status != "active":
        raise HTTPException(404, "unknown project")
    ws_id = project.workspace_id
    permissions.require_member(db, user, ws_id, permissions.PROJECT_EDIT)
    entitlements.require_feature(db, ws_id, f"{project.tool_key}.access")
    count = db.execute(select(func.count()).select_from(Document).where(
        Document.workspace_id == ws_id, Document.project_id == project_id)).scalar_one()
    entitlements.require_quota(db, ws_id, f"{project.tool_key}.documents.max", count)

    if (file.filename or "").lower().rsplit(".", 1)[-1] != "pdf":
        raise HTTPException(400, "only PDF uploads are supported")
    max_mb = entitlements.require_feature(db, ws_id, f"{project.tool_key}.upload_mb.max")

    doc = Document(workspace_id=ws_id, project_id=project_id,
                   name=(file.filename or "document.pdf")[:300])
    db.add(doc)
    db.flush()
    key = source_key(ws_id, project_id, doc.id)
    storage = get_storage()
    size = storage.save_stream(key, file.file)
    if max_mb is not None and size > max_mb * 1024 * 1024:
        storage.delete_prefix(f"workspaces/{ws_id}/projects/{project_id}/documents/{doc.id}")
        db.delete(doc)
        db.commit()
        raise HTTPException(413, f"file exceeds the {max_mb} MB limit")
    doc.storage_key = key
    doc.size_bytes = size

    run = Run(document_id=doc.id)
    db.add(run)
    db.flush()
    run.storage_prefix = run_prefix(ws_id, project_id, doc.id, run.id)
    job = jobs.enqueue(db, "convert",
                       {"document_id": str(doc.id), "run_id": str(run.id)},
                       workspace_id=ws_id)
    audit.record(db, "document.upload", actor=user.id, workspace=ws_id,
                 target_type="document", target_id=str(doc.id),
                 data={"bytes": size})
    db.commit()
    return {"document": {"id": str(doc.id), "name": doc.name, "status": doc.status},
            "run": {"id": str(run.id)}, "job": {"id": str(job.id), "status": job.status}}


@router.get("/api/platform/documents/{doc_id}")
def document_status(doc_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    user, _ = _auth(db, request)
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "unknown document")
    permissions.require_member(db, user, doc.workspace_id, permissions.PROJECT_VIEW)
    runs = db.execute(select(Run).where(Run.document_id == doc.id)
                      .order_by(Run.created_at.desc())).scalars().all()
    out_runs = []
    for r in runs:
        arts = db.execute(select(Artifact).where(Artifact.run_id == r.id)).scalars().all()
        out_runs.append({"id": str(r.id), "status": r.status, "error": r.error,
                         "artifacts": [{"id": str(a.id), "kind": a.kind,
                                        "path": a.rel_path, "bytes": a.size_bytes}
                                       for a in arts]})
    return {"id": str(doc.id), "name": doc.name, "status": doc.status,
            "pages": doc.pages, "runs": out_runs}


@router.get("/api/platform/jobs/{job_id}")
def job_status(job_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    user, _ = _auth(db, request)
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "unknown job")
    if job.workspace_id is not None:
        permissions.require_member(db, user, job.workspace_id, permissions.PROJECT_VIEW)
    elif user.platform_role != "platform_admin":
        raise HTTPException(404, "unknown job")
    return {"id": str(job.id), "kind": job.kind, "status": job.status,
            "attempts": job.attempts, "error": job.error}


# --------------------------------------------------- private artifact serving

@router.get("/api/files/{artifact_id}")
def serve_artifact(artifact_id: uuid.UUID, request: Request,
                   db: Session = Depends(get_db)):
    """The private replacement for the public /output mount: membership in the
    owning workspace is checked on every fetch. (S3 later: same route returns
    a short-lived presigned redirect instead of a FileResponse.)"""
    user, _ = _auth(db, request)
    art = db.get(Artifact, artifact_id)
    if art is None:
        raise HTTPException(404, "unknown artifact")
    run = db.get(Run, art.run_id)
    doc = db.get(Document, run.document_id) if run else None
    if doc is None:
        raise HTTPException(404, "unknown artifact")
    permissions.require_member(db, user, doc.workspace_id, permissions.PROJECT_VIEW)
    path = get_storage().path(f"{run.storage_prefix}/{art.rel_path}")
    if not path.exists():
        raise HTTPException(404, "artifact file missing")
    return FileResponse(path)
