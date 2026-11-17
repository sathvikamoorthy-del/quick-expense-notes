"""Sign-in rules (REQ-275) against a SQLite database built by the real migrations (0001 to 0003)."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import jwt
import pytest

from app.auth.jwt import AuthConfigError, AuthSettings
from app.auth.service import (
    InvalidCredentials,
    PasswordTooShort,
    check_password,
    hash_password,
    issue_token,
    normalise_email,
    sign_in,
    upsert_user,
)
from app.db.session import Database
from scripts.seed_users import DEMO_EMAIL, seed

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
SECRET = "s" * 40
PASSWORD = "correct-horse-1"


def build_users_db(directory: Path) -> Path:
    """Categories, merchants and their seed, plus the users table (also used by test_routes)."""
    path = directory / "app.db"
    connection = sqlite3.connect(path)
    try:
        for name in ("0001_db_design.sql", "0002_seed_reference.sql", "0003_users.sql"):
            connection.executescript((MIGRATIONS / name).read_text(encoding="utf-8"))
    finally:
        connection.close()
    return path


@pytest.fixture
def db_file(tmp_path: Path) -> Path:
    return build_users_db(tmp_path)


@pytest.fixture
async def database(db_file: Path):
    db = Database.from_url(f"file:{db_file}")
    async with db.sessions() as session:
        await upsert_user(session, "Asha@Example.com", PASSWORD, "Asha")
        await session.commit()
    yield db
    await db.dispose()


def settings() -> AuthSettings:
    return AuthSettings(jwt_secret=SECRET)


def test_email_is_trimmed_and_lower_cased():
    assert normalise_email("  Asha@Example.COM ") == "asha@example.com"


def test_hash_is_bcrypt_and_never_the_password():
    hashed = hash_password(PASSWORD)
    assert hashed.startswith("$2b$")
    assert PASSWORD not in hashed
    assert check_password(PASSWORD, hashed)
    assert not check_password("wrong-password", hashed)


def test_password_shorter_than_8_characters_is_refused():
    with pytest.raises(PasswordTooShort):
        hash_password("1234567")
    assert hash_password("12345678").startswith("$2b$")


def test_a_bad_hash_or_overlong_password_never_matches():
    assert not check_password(PASSWORD, "not-a-hash")
    assert not check_password("x" * 100, hash_password(PASSWORD))


def test_token_expires_60_minutes_after_issue():
    issued = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
    token = issue_token("user-1", now=issued, settings=settings())
    claims = jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_exp": False})
    assert claims["sub"] == "user-1"
    assert claims["exp"] - claims["iat"] == 3600
    assert claims["iat"] == int(issued.timestamp())


def test_token_carries_issuer_and_audience_when_configured():
    cfg = AuthSettings(jwt_secret=SECRET, jwt_issuer="qen", jwt_audience="web")
    claims = jwt.decode(issue_token("u", settings=cfg), SECRET, algorithms=["HS256"], audience="web", issuer="qen")
    assert claims["iss"] == "qen" and claims["aud"] == "web"


def test_no_token_without_a_long_enough_secret():
    with pytest.raises(AuthConfigError):
        issue_token("u", settings=AuthSettings(jwt_secret="short"))


async def test_sign_in_ignores_email_case(database):
    async with database.sessions() as session:
        result = await sign_in(session, "ASHA@example.com", PASSWORD, settings=settings())
    assert result.email == "asha@example.com"
    assert result.display_name == "Asha"
    assert result.expires_in == 3600
    assert jwt.decode(result.token, SECRET, algorithms=["HS256"])["sub"] == result.user_id


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("asha@example.com", "wrong-password"),
        ("nobody@example.com", PASSWORD),
        ("", PASSWORD),
        ("asha@example.com", ""),
    ],
)
async def test_bad_details_all_raise_the_same_error(database, email, password):
    async with database.sessions() as session:
        with pytest.raises(InvalidCredentials):
            await sign_in(session, email, password, settings=settings())


async def test_database_holds_only_the_hash(database, db_file):
    connection = sqlite3.connect(db_file)
    try:
        rows = connection.execute("SELECT email, password_hash FROM users").fetchall()
    finally:
        connection.close()
    assert rows[0][0] == "asha@example.com"
    assert rows[0][1].startswith("$2b$") and PASSWORD not in rows[0][1]


async def test_upsert_updates_an_existing_account(database):
    async with database.sessions() as session:
        first = await upsert_user(session, "asha@example.com", "new-password-1", "Asha R")
        await session.commit()
    async with database.sessions() as session:
        result = await sign_in(session, "asha@example.com", "new-password-1", settings=settings())
    assert result.user_id == first.id and result.display_name == "Asha R"


async def test_upsert_refuses_an_empty_email():
    with pytest.raises(ValueError):
        await upsert_user(None, " ", PASSWORD, "Asha")  # type: ignore[arg-type]


async def test_seed_script_creates_the_demo_user(db_file):
    user_id = await seed(PASSWORD, url=f"file:{db_file}")
    connection = sqlite3.connect(db_file)
    try:
        row = connection.execute("SELECT id, email, display_name FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        connection.close()
    assert row == (user_id, DEMO_EMAIL, "Asha")
