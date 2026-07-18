"""RK3 platform layer — multi-tenant foundation (Stage 1).

Identity / authorization / entitlements are deliberately separate concerns
(see docs/DEFERRED/multi-user-platform-plan.md and
sources/docs/plans/multiuser-stage1-execution.md):

- identity lives with the OIDC provider (Keycloak when stood up; a dev
  identity on this box) — `auth.py` / `oidc.py`;
- authorization (who may do what in a workspace) lives here — `permissions.py`;
- entitlements (what the workspace has obtained) live here — `entitlements.py`.

PostgreSQL is the source of truth (`models.py`), private files live behind
`storage.py`, background work is durable in the `jobs` table and executed by
`worker.py`.
"""
