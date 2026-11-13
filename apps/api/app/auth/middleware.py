"""authenticate: identifies the caller. require_auth and require_role guard the routes that need a signed-in user.

No Authorization header = anonymous (request.state.auth is None). A token that is present but not valid, or a malformed
Bearer header, is 401 with one answer for every kind of bad token. A valid token sets request.state.auth.
"""

import re
from collections.abc import Awaitable, Callable

import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from app.auth.jwt import AuthClaims, AuthConfigError, verify_token

_BEARER_PREFIX = re.compile(r"^bearer\b", re.IGNORECASE)
_BEARER = re.compile(r"^Bearer\s+(\S+)$", re.IGNORECASE)


def _bearer(header: str | None) -> str | None:
    """None = no bearer credentials (anonymous); "" = a token was sent but the header is malformed."""
    if header is None or not _BEARER_PREFIX.match(header.strip()):
        return None
    match = _BEARER.match(header.strip())
    return match.group(1) if match else ""


async def _authenticate(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    request.state.auth = None
    token = _bearer(request.headers.get("authorization"))
    if token is not None:
        try:
            if not token:
                raise jwt.InvalidTokenError("malformed bearer header")
            request.state.auth = verify_token(token)
        except AuthConfigError:
            return JSONResponse({"error": "auth-misconfigured"}, status_code=500)
        except jwt.PyJWTError:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
    return await call_next(request)


def authenticate(app: FastAPI) -> None:
    """Registered in the middleware glue (outermost: tenant resolution and auditing read request.state.auth)."""
    app.middleware("http")(_authenticate)


def current_auth(request: Request) -> AuthClaims | None:
    auth: AuthClaims | None = getattr(request.state, "auth", None)
    return auth


def require_auth(request: Request) -> AuthClaims:
    """Dependency: 401 unless a valid token was sent."""
    auth = current_auth(request)
    if auth is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return auth


def require_role(role: str) -> Callable[[Request], AuthClaims]:
    """Dependency factory: 401 when anonymous, 403 when the caller lacks the role."""

    def guard(request: Request) -> AuthClaims:
        auth = require_auth(request)
        if role not in auth.roles:
            raise HTTPException(status_code=403, detail="forbidden")
        return auth

    return guard
