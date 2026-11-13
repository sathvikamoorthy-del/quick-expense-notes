"""Verification of signed access tokens (HS256) with PyJWT. Tokens are issued elsewhere (same claims as the Node API).

The secret comes from JWT_SECRET (at least 32 characters) and nowhere else.
"""

from dataclasses import dataclass, field
from typing import Any

import jwt
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthConfigError(Exception):
    """JWT_SECRET is missing or too short: authentication fails closed."""


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    jwt_secret: str = ""  # JWT_SECRET
    jwt_issuer: str | None = None  # JWT_ISSUER: checked when set
    jwt_audience: str | None = None  # JWT_AUDIENCE: checked when set


@dataclass(frozen=True)
class AuthClaims:
    user_id: str
    tenant_id: str | None = None
    roles: list[str] = field(default_factory=list)
    claims: dict[str, Any] = field(default_factory=dict)


def verify_token(token: str, settings: AuthSettings | None = None) -> AuthClaims:
    """Only HS256 is accepted (never "none" or another algorithm); exp and sub are required; issuer and audience
    are checked when configured. Raises AuthConfigError for a bad configuration and jwt.PyJWTError for a bad token."""
    cfg = settings or AuthSettings()
    if len(cfg.jwt_secret) < 32:
        raise AuthConfigError("JWT_SECRET must be set to a random string of at least 32 characters")
    payload = jwt.decode(
        token,
        cfg.jwt_secret,
        algorithms=["HS256"],
        issuer=cfg.jwt_issuer,
        audience=cfg.jwt_audience,
        options={"require": ["exp", "sub"], "verify_aud": cfg.jwt_audience is not None},
    )
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise jwt.InvalidTokenError("token has no subject")
    tenant = payload.get("tenantId")
    roles = payload.get("roles")
    return AuthClaims(
        user_id=subject,
        tenant_id=tenant if isinstance(tenant, str) else None,
        roles=[r for r in roles if isinstance(r, str)] if isinstance(roles, list) else [],
        claims=payload,
    )
