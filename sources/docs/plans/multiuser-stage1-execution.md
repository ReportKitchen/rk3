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

## Identity: ZITADEL — STOOD UP (2026-07-18, owner chose it; AGPL accepted)

ZITADEL v4.16.1 runs on this box as the identity provider — a single Go
binary against our existing PostgreSQL (that's why it beat Keycloak here: no
JVM, no container).

- **Service**: `systemctl status zitadel` (unit tracked at
  `development/zitadel/zitadel.service` → `run-zitadel.sh`, which pulls
  secrets from `.env`: `ZITADEL_DB_PASSWORD`, `ZITADEL_MASTERKEY`,
  `ZITADEL_ADMIN_PASSWORD`). Issuer/console: `http://localhost:9800`
  (console login: `rk-admin@rk3.local` / `ZITADEL_ADMIN_PASSWORD` from .env).
- **DB**: role+db `zitadel` on the same Postgres 16.
- **RK3 OIDC app**: project `rk3` / app `rk3-web` (client id + secret in
  `.env` as `RK3_OIDC_*`), created via the bootstrap machine-user PAT
  (`development/zitadel/bootstrap.pat` — gitignored, it's a live credential).
- **Login v1 note**: ZITADEL v4 defaults to its NEW login (a separate
  Next.js service the bare binary doesn't ship). The instance feature
  `loginV2.required=false` is set, so the BUILT-IN v1 login page serves.
  Deploying login-v2 is optional later polish.
- **VERIFIED end-to-end**: anonymous visit → redirect → real ZITADEL
  password login (test user `testuser@rk3.local`) → PKCE code exchange →
  id_token JWKS-verified → userinfo enrichment (ZITADEL doesn't assert
  email/profile into the id_token by default; `oidc.py` falls back to the
  userinfo endpoint — portable across providers) → user upserted by subject →
  personal workspace auto-created with `lpm_free` → session cookie → app.
- **To flip the main app to real login**: set `RK3_AUTH_MODE=oidc` and
  `RK3_OIDC_REDIRECT_URL=http://127.0.0.1:8300/api/auth/callback` in `.env`
  (the :8300 redirect URI is already registered on the app) and restart rk3.
  Dev mode remains the default on this box for frictionless work.
- **Still parked within identity**: SMTP/SES wiring (self-registration email
  verification + recovery need it), a production domain + TLS
  (ExternalDomain/ExternalSecure), and the signup UX beyond ZITADEL's stock
  register screen.

## Changing the free-tier limits (owner: "document where to change them")

The numbers are `plan_entitlements` rows, read per request — no restart:

```sql
-- current limits
sudo -u postgres psql rk3 -c \
  "SELECT feature, limit_int FROM plan_entitlements WHERE plan_key='lpm_free';"
-- e.g. raise the project cap
sudo -u postgres psql rk3 -c \
  "UPDATE plan_entitlements SET limit_int=10 \
   WHERE plan_key='lpm_free' AND feature='lpm.projects.max';"
```

Per-workspace exceptions: add an `entitlement_grants` row
(`source='admin_grant'`, optional `valid_until`, a `reason`) — the most
generous valid grant wins.

## S3 + SES — wired (2026-07-20, owner delivered creds)

- **S3 (`rk3-storage`, us-east-1)**: `S3Storage` implements the same adapter
  interface (worker contract: `download_to` source → convert in a temp dir →
  `upload_dir` outputs; serving: 307 redirect to a short-lived presigned URL).
  The worker is now backend-agnostic — the local backend uses the identical
  temp-dir flow. **Every primitive round-tripped live against the bucket**
  (save/exists/download_to/upload_dir/presigned-GET/delete). This box stays
  `RK3_STORAGE_BACKEND=local`; production flips one env var (+ bucket/region
  already in `.env`).
- **SES SMTP**: credentials are derived from the IAM secret (documented AWS
  derivation) — auth verified against all US SMTP endpoints. ZITADEL's SMTP
  config is SET AND ACTIVATED (SES us-east-1, sender
  `noreply@reportkitchen.com`). **Blocked on exactly one owner action: verify
  an SES identity** — verify the `reportkitchen.com` DOMAIN in the SES console
  (adds DKIM DNS records; enables any @reportkitchen.com sender), and request
  production access to leave the SES sandbox. Until then sends get
  `554 not verified` (tested).

## Domain shape (owner considering app.reportkitchen.com)

- `www.` (WordPress) = marketing. **Links only, never a credentials form** —
  passwords are typed exclusively on the IdP origin (the OIDC security model).
  - Log in button → `https://app.reportkitchen.com/api/auth/login`
  - Sign up button → `…/api/auth/login?signup=1` (prompt=create → lands on
    the registration form)
  - Email-capture form → `…/api/auth/login?signup=1&login_hint=<email>`
    (prefills the form; the form collects ONLY the email)
- `app.` = RK3 (FastAPI + SPA). `auth.` = ZITADEL (it needs its own hostname:
  ExternalDomain/ExternalSecure + TLS at go-live).

## PARKED — needs the owner

1. **AWS remaining**: RDS (Postgres is box-local), SES **identity
   verification + production access** (see above — the one email blocker).
2. **Decisions 4–10**: **ANSWERED 2026-07-18** — recorded inline in
   `docs/DEFERRED/multi-user-platform-plan.md` (teams paid-only; seeded free
   limits stand; per-workspace pricing w/ usage tiers; project belongs to the
   workspace; lapsed plan = workspace unavailable [Stage 3 implements];
   no pruning yet; export-only, no public sharing).
4. **login-v2 before live-live** (owner): self-host ZITADEL's login-v2 app at
   auth. to collapse the Front Door -> IdP two-step into one styled screen.
   (The customer shell itself SHIPPED 2026-07-20 — Front Door / Home / editor
   on the docbridge; see the shell commit for the full picture.)
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
