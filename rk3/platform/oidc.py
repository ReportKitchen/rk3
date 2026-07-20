"""OIDC Authorization Code + PKCE, backend-for-frontend (plan §Keycloak).

Provider-agnostic: everything is driven by the issuer's discovery document, so
Keycloak or ZITADEL is a matter of four .env values (RK3_OIDC_ISSUER,
RK3_OIDC_CLIENT_ID, RK3_OIDC_CLIENT_SECRET, RK3_OIDC_REDIRECT_URL) and
RK3_AUTH_MODE=oidc. FastAPI does the code exchange; the browser only ever
sees our session cookie. The in-flight state+verifier ride in a short-lived
signed cookie so no server storage is needed before login completes.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import time

import httpx
from authlib.jose import JsonWebToken
from itsdangerous import BadSignature, URLSafeSerializer

from rk3.platform import config

_FLOW_COOKIE = "rk3_oidc_flow"
_FLOW_TTL = 600  # seconds to complete a login round-trip

_discovery_cache: dict | None = None
_jwks_cache: dict | None = None


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(config.SESSION_SECRET, salt="rk3-oidc-flow")


def discovery() -> dict:
    global _discovery_cache
    if _discovery_cache is None:
        url = config.OIDC_ISSUER.rstrip("/") + "/.well-known/openid-configuration"
        _discovery_cache = httpx.get(url, timeout=10).raise_for_status().json()
    return _discovery_cache


def _jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        _jwks_cache = httpx.get(discovery()["jwks_uri"], timeout=10).raise_for_status().json()
    return _jwks_cache


def begin_login(login_hint: str = "", signup: bool = False) -> tuple[str, str]:
    """-> (authorization redirect URL, signed flow-cookie value).

    `login_hint` prefills the identifier (the marketing-site email-capture
    pattern: www collects ONLY the email and forwards it — passwords are never
    typed anywhere but the IdP). `signup` sends prompt=create so a "Sign up"
    button lands on the registration form, not the login form."""
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(24)
    flow = _serializer().dumps({"v": verifier, "s": state, "t": int(time.time())})
    from urllib.parse import urlencode
    params = {
        "response_type": "code",
        "client_id": config.OIDC_CLIENT_ID,
        "redirect_uri": config.OIDC_REDIRECT_URL,
        "scope": "openid email profile",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if login_hint:
        params["login_hint"] = login_hint[:320]
    if signup:
        params["prompt"] = "create"
    url = discovery()["authorization_endpoint"] + "?" + urlencode(params)
    return url, flow


def finish_login(code: str, state: str, flow_cookie: str) -> dict:
    """Exchange the code (PKCE) and return verified claims {sub, email, name}."""
    try:
        flow = _serializer().loads(flow_cookie)
    except BadSignature as e:
        raise ValueError("login flow cookie invalid") from e
    if state != flow.get("s") or int(time.time()) - int(flow.get("t", 0)) > _FLOW_TTL:
        raise ValueError("login flow expired or state mismatch")

    token = httpx.post(discovery()["token_endpoint"], data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.OIDC_REDIRECT_URL,
        "client_id": config.OIDC_CLIENT_ID,
        "client_secret": config.OIDC_CLIENT_SECRET,
        "code_verifier": flow["v"],
    }, timeout=15).raise_for_status().json()

    jwt = JsonWebToken(["RS256", "ES256"])
    claims = jwt.decode(token["id_token"], _jwks())
    claims.validate()
    if claims.get("iss") != config.OIDC_ISSUER:
        raise ValueError("issuer mismatch")
    if config.OIDC_CLIENT_ID not in ([claims.get("aud")] if isinstance(claims.get("aud"), str) else (claims.get("aud") or [])):
        raise ValueError("audience mismatch")
    out = {
        "sub": claims["sub"],
        "email": claims.get("email") or "",
        "name": claims.get("name") or claims.get("preferred_username") or "",
    }
    # Not every provider asserts profile claims into the id_token (ZITADEL
    # doesn't by default) — the userinfo endpoint is the portable source.
    if not out["email"] or not out["name"]:
        try:
            ui = httpx.get(discovery()["userinfo_endpoint"],
                           headers={"Authorization": f"Bearer {token['access_token']}"},
                           timeout=10).raise_for_status().json()
            out["email"] = out["email"] or ui.get("email") or ""
            out["name"] = out["name"] or ui.get("name") or ui.get("preferred_username") or ""
        except httpx.HTTPError:
            pass  # claims stay as asserted; the profile can fill in next login
    return out


FLOW_COOKIE = _FLOW_COOKIE
FLOW_TTL = _FLOW_TTL
