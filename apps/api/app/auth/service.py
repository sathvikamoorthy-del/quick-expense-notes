"""Sign-in rules (REQ-275): email and password, checked against a bcrypt hash, answered with a 60-minute JWT.

An empty email or password, an unknown email and a wrong password all raise the same InvalidCredentials, so the
caller cannot tell which one was wrong. An unknown email is still checked against a dummy hash, so it takes about as
long as a wrong password.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import AuthConfigError, AuthSettings
from app.models.users import Users

INVALID_CREDENTIALS = "Invalid email or password."
MIN_PASSWORD_LENGTH = 8
TOKEN_LIFETIME = timedelta(minutes=60)


class InvalidCredentials(Exception):
    """Empty email or password, unknown email or wrong password: one answer for all of them."""


class PasswordTooShort(ValueError):
    pass


@dataclass(frozen=True)
class SignedIn:
    token: str
    expires_in: int
    user_id: str
    email: str
    display_name: str


def normalise_email(email: str) -> str:
    """Emails are not case-sensitive: Asha@Example.com and asha@example.com are one account."""
    return email.strip().lower()


def hash_password(password: str) -> str:
    """bcrypt hash of a password of at least 8 characters (bcrypt itself refuses more than 72 bytes)."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordTooShort(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def check_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:  # longer than bcrypt accepts, or not a bcrypt hash: never a match
        return False


@cache
def _dummy_hash() -> str:
    return bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt()).decode("ascii")


def issue_token(user_id: str, now: datetime | None = None, settings: AuthSettings | None = None) -> str:
    """HS256 token with sub, iat and exp (60 minutes); iss and aud when configured, as verify_token expects."""
    cfg = settings or AuthSettings()
    if len(cfg.jwt_secret) < 32:
        raise AuthConfigError("JWT_SECRET must be set to a random string of at least 32 characters")
    issued = now or datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": user_id,
        "iat": int(issued.timestamp()),
        "exp": int((issued + TOKEN_LIFETIME).timestamp()),
    }
    if cfg.jwt_issuer:
        payload["iss"] = cfg.jwt_issuer
    if cfg.jwt_audience:
        payload["aud"] = cfg.jwt_audience
    return jwt.encode(payload, cfg.jwt_secret, algorithm="HS256")


async def sign_in(session: AsyncSession, email: str, password: str, settings: AuthSettings | None = None) -> SignedIn:
    normalised = normalise_email(email)
    if not normalised or not password.strip():
        raise InvalidCredentials
    user = (await session.execute(select(Users).where(Users.email == normalised))).scalar_one_or_none()
    if user is None:
        check_password(password, _dummy_hash())
        raise InvalidCredentials
    if not check_password(password, user.password_hash):
        raise InvalidCredentials
    return SignedIn(
        token=issue_token(user.id, settings=settings),
        expires_in=int(TOKEN_LIFETIME.total_seconds()),
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
    )


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


async def upsert_user(session: AsyncSession, email: str, password: str, display_name: str) -> Users:
    """Creates the account, or sets a new password and name on an existing one (used by the seed script)."""
    normalised = normalise_email(email)
    if not normalised or not display_name.strip():
        raise ValueError("email and display name must not be empty")
    password_hash = hash_password(password)
    user = (await session.execute(select(Users).where(Users.email == normalised))).scalar_one_or_none()
    now = _now_iso()
    if user is None:
        user = Users(
            id=str(uuid.uuid4()),
            email=normalised,
            password_hash=password_hash,
            display_name=display_name.strip(),
            created_at=now,
            updated_at=now,
        )
        session.add(user)
    else:
        user.password_hash = password_hash
        user.display_name = display_name.strip()
        user.updated_at = now
    await session.flush()
    return user
