"""Platform configuration — env-driven, `.env`-seeded (same loader contract as
rk3.ai: real environment wins, `.env` fills gaps). Nothing here is committed;
secrets live in `.env` only."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())


_load_env()

DATABASE_URL = os.environ.get("RK3_DATABASE_URL", "")
SESSION_SECRET = os.environ.get("RK3_SESSION_SECRET", "")
# dev = seeded-owner login via /api/auth/dev-login (this box);
# oidc = Authorization Code + PKCE against OIDC_ISSUER (Keycloak/ZITADEL)
AUTH_MODE = os.environ.get("RK3_AUTH_MODE", "oidc")

OIDC_ISSUER = os.environ.get("RK3_OIDC_ISSUER", "")
OIDC_CLIENT_ID = os.environ.get("RK3_OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.environ.get("RK3_OIDC_CLIENT_SECRET", "")
OIDC_REDIRECT_URL = os.environ.get("RK3_OIDC_REDIRECT_URL", "")

# private file tree (NOT under the public /output mount)
STORAGE_ROOT = Path(os.environ.get("RK3_STORAGE_ROOT", str(ROOT / "storage")))
# storage backend: local (this box) | s3 (production)
STORAGE_BACKEND = os.environ.get("RK3_STORAGE_BACKEND", "local")
S3_BUCKET = os.environ.get("RK3_S3_BUCKET", "")
S3_REGION = os.environ.get("RK3_S3_REGION", "us-east-1")
S3_ACCESS_KEY = os.environ.get("AWS_S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("AWS_S3_SECRET_KEY", "")

SESSION_TTL_DAYS = int(os.environ.get("RK3_SESSION_TTL_DAYS", "30"))
SESSION_COOKIE = "rk3_session"
CSRF_COOKIE = "rk3_csrf"
CSRF_HEADER = "x-csrf-token"

DEV_USER_EMAIL = os.environ.get("RK3_DEV_EMAIL", "dev@rk3.local")
DEV_USER_SUBJECT = "dev:owner"

WORKER_POLL_SECONDS = float(os.environ.get("RK3_WORKER_POLL_SECONDS", "2"))
CONVERT_TIMEOUT_SECONDS = int(os.environ.get("RK3_CONVERT_TIMEOUT", "3600"))
