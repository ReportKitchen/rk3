# Multiuser Stage 1 — execution plan (in progress)

**Source:** `docs/DEFERRED/multi-user-platform-plan.md` (owner, 2026-07-18) —
adopted with the revisions below. This doc tracks what is BUILT, what is
PARKED for the owner, and the decisions taken en route. Started 2026-07-18 with
the owner away ("proceed as far as you can go, parking anything you need me for").

## Adopted architecture (unchanged from the owner's plan)

Multi-tenant modular monolith. FastAPI backend-for-frontend, PostgreSQL as the
source of truth (users/workspaces/memberships/entitlements/projects/jobs/
audit), private object storage for documents+artifacts, durable worker queue,
OIDC identity (Keycloak when stood up), Stripe only at paid launch. Identity /
authorization / entitlements kept strictly separate. Every signup gets a
personal workspace; tenant is called `workspace` internally.

## Revisions I made (and why)

1. **Postgres now, on this box.** PostgreSQL 16 is already installed and
   running here, so the foundation uses it directly (no SQLite interim). Role
   `rk3`, databases `rk3` + `rk3_test`; `DATABASE_URL` in `.env`.
2. **Jobs: Postgres-durable + own small worker, no Redis/Dramatiq yet.** The
   plan's hard requirement is "jobs as durable DB truth + dedicated worker".
   Redis/Dramatiq is an operational dependency the box doesn't have; a
   `FOR UPDATE SKIP LOCKED` claim loop in a separate worker process satisfies
   durability, retries, idempotency, and concurrency caps for one box. The
   jobs table is broker-agnostic — Dramatiq can be layered on later without
   schema change.
3. **Auth ships in two modes behind one session layer.** `AUTH_MODE=oidc` is
   the real thing (Authorization Code + PKCE via authlib, discovery-driven, so
   Keycloak OR ZITADEL works, tokens server-side only, HttpOnly session
   cookie, CSRF double-submit on state-changing routes). `AUTH_MODE=dev` gives
   this box a frictionless seeded-owner login (explicit `/api/auth/dev-login`,
   never silent) so development continues while Keycloak stand-up is parked.
   Sessions live in the DB (revocable, per the admin requirements).
4. **The existing corpus becomes the `internal` workspace immediately**
   (plan Stage 4 pulled forward as a seed step): a `workspace` row of type
   `internal`, every current `sources/` doc gets a `documents` row flagged
   `legacy=true` pointing at its existing path. Nothing moves; the current app
   keeps working exactly as-is and is understood as the staff surface.
   New uploads go to the private storage tree only.
5. **Pipeline entry refactor is minimal**: internals already run on explicit
   `(source, outdir)` (`Context`); added `convert_paths(source, outdir)` +
   `python -m rk3 convert-path <src> <out>` and the slug entry now delegates.
   The worker converts uploaded documents in the private tree via the same
   subprocess isolation the app already uses.
6. **Private artifacts route now, S3 later.** `storage.py` is an adapter:
   `LocalDiskStorage` under `storage/` (gitignored, outside the public
   `/output` mount) with the plan's exact key layout
   (`workspaces/<ws>/projects/<proj>/documents/<doc>/source.pdf`,
   `runs/<run>/…`); an `S3Storage` implements the same interface when AWS
   exists (presigned URLs slot into the same serving endpoint).
7. **Free-tier limits are seeded as placeholder numbers** (decision 5 is the
   owner's): `lpm.access`, `lpm.projects.max=3`, `lpm.documents.max=5`,
   `lpm.upload_mb.max=50`, `lpm.pages.max=150`, `lpm.ai_generations.monthly=20`.
   One row each in `plan_entitlements` — change the numbers, not the code.

## Built (this pass)

- [x] `rk3/platform/` package: `config` `db` `models` `permissions`
      `entitlements` `auth` `oidc` `storage` `jobs` `audit` `seed`
- [x] Alembic migration baseline (`alembic/` at repo root, ini included)
- [x] `app/platform_api.py` mounted under `/api/auth/*` + `/api/platform/*` +
      `/api/files/{artifact}`; existing routes untouched
- [x] Durable worker (`python -m rk3.platform.worker`) + `rk3-worker.service`
- [x] Seed: tools/plans catalog, internal workspace + corpus import, dev user
- [x] SPA boots through `/api/me` (dev mode auto-establishes the session; UX
      on this box unchanged)
- [x] Tests: permission matrix, entitlement/quota checks, job lifecycle
      (claim/retry/finish), auth session + CSRF, upload→convert E2E
- [x] E2E verified on this box: dev-login → create project → upload PDF →
      worker converts → artifacts served through the membership-checked route;
      anonymous and cross-workspace access refused
- [x] Project state endpoints with optimistic concurrency (GET/PUT
      `/api/platform/projects/{id}/state`, version check → 409 on stale — the
      plan's conflict baseline; LPM sidecar migration will write here)
- [x] Minimal platform-admin read surface (staff-only, 404-unadvertised):
      `/api/platform/admin/overview` | `/admin/audit` | `/admin/jobs`

## PARKED — needs the owner

1. **AWS**: RDS, private S3 bucket, SES (and IAM). Until then: local Postgres,
   local private storage tree, no email (so no verification/recovery — which
   is also why Keycloak stand-up is pointless this second).
2. **Keycloak**: no Docker/Java on this box. Decide Keycloak vs ZITADEL
   (plan recommends Keycloak; AGPL review for ZITADEL), then stand it up and
   fill `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`,
   `OIDC_REDIRECT_URL` in `.env` and set `AUTH_MODE=oidc`. The client side is
   built and discovery-driven.
3. **Decisions 4–10** from the plan (team creation for free users, real free
   limits, pricing shape, per-project ACLs, end-of-plan behavior, retention,
   public hosting vs export-only). Placeholders noted above.
4. **Customer-facing app shell**: Stage 1's "private project list + upload"
   UI for LPM-only customers (the current SPA is the staff/internal surface).
   Needs a design pass — parked rather than improvised.
5. **Untrusted-PDF isolation** for public launch: separate worker
   container/host, resource limits, egress control (plan §pipeline). The
   worker currently isolates via subprocess + timeout like the existing app.
6. **TLS/domain/cookie-Secure/observability**, terms/privacy text, analytics
   bootstrap (`docs/DEFERRED/landing-page-maker-analytics-plan.md`).
7. **requirements manifest**: new Python deps are in the venv only
   (sqlalchemy, alembic, psycopg[binary], authlib, itsdangerous, css-inline).
   Worth starting a `requirements.txt` when infra work begins.

## Operating notes (this box)

- DB: `sudo -u postgres psql`; app connects as role `rk3` (password in `.env`,
  never committed). Test DB `rk3_test` is dropped/recreated by the test suite.
- Migrations: `.venv/bin/alembic upgrade head` from the repo root.
- Worker: `systemctl status rk3-worker` (unit installed; runs
  `python -m rk3.platform.worker`).
- Storage tree: `<repo>/storage/` (gitignored).
