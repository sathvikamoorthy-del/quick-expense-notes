"""POST /auth/sign-in and the 401 boundary of the protected routes (REQ-275)."""

import asyncio
import time
from datetime import UTC, date, datetime, timedelta

import jwt
import pytest

from app.auth.jwt import AuthSettings
from app.auth.service import issue_token
from app.entries.codes import clear_codes_cache
from app.http.app import create_app
from app.http.settings import Settings
from scripts.seed_users import seed
from tests.auth.test_service import build_users_db
from tests.helpers import client_for

SECRET = "s" * 40
PASSWORD = "correct-horse-1"
MESSAGE = {"error": "Invalid email or password."}


@pytest.fixture
def client(tmp_path, monkeypatch):
    clear_codes_cache()
    db_file = build_users_db(tmp_path)
    asyncio.run(seed(PASSWORD, url=f"file:{db_file}"))
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("DATABASE_URL", f"file:{db_file}")
    monkeypatch.setattr("app.entries.routes.today_ist", lambda: date(2026, 11, 17))
    with client_for(create_app(settings=Settings(env="development"))) as test_client:
        yield test_client
    clear_codes_cache()


def sign_in(client, email="asha@example.com", password=PASSWORD):
    return client.post("/auth/sign-in", json={"email": email, "password": password})


def expand(client, headers=None):
    return client.post("/entries/expand", json={"text": "SWG 340 yd"}, headers=headers or {})


def test_correct_details_return_a_token_that_opens_the_entry_box(client):
    response = sign_in(client)
    assert response.status_code == 200
    body = response.json()
    assert body["expires_in"] == 3600
    assert body["user"]["email"] == "asha@example.com"
    assert body["user"]["display_name"] == "Asha"
    assert "password" not in response.text
    opened = expand(client, {"Authorization": f"Bearer {body['token']}"})
    assert opened.status_code == 200 and opened.json()["ok"] is True


def test_email_in_different_case_signs_in(client):
    assert sign_in(client, email="ASHA@Example.com").status_code == 200


def test_wrong_password_is_401_with_the_shared_message(client):
    response = sign_in(client, password="wrong-password")
    assert response.status_code == 401 and response.json() == MESSAGE


def test_unknown_email_is_401_with_the_same_message(client):
    response = sign_in(client, email="nobody@example.com")
    assert response.status_code == 401 and response.json() == MESSAGE


@pytest.mark.parametrize(("email", "password"), [("", PASSWORD), ("asha@example.com", ""), ("", ""), ("  ", "  ")])
def test_sign_in_empty_email_or_password_is_401(client, email, password):
    response = sign_in(client, email=email, password=password)
    assert response.status_code == 401
    assert response.json() == MESSAGE


def test_no_token_is_401(client):
    assert expand(client).status_code == 401


def test_wrongly_signed_token_is_401(client):
    forged = jwt.encode({"sub": "x", "exp": int(time.time()) + 60}, "f" * 40, algorithm="HS256")
    assert expand(client, {"Authorization": f"Bearer {forged}"}).status_code == 401


def test_token_stops_working_60_minutes_after_sign_in(client):
    cfg = AuthSettings(jwt_secret=SECRET)
    still_valid = issue_token("user-1", now=datetime.now(UTC) - timedelta(minutes=59), settings=cfg)
    expired = issue_token("user-1", now=datetime.now(UTC) - timedelta(minutes=61), settings=cfg)
    assert expand(client, {"Authorization": f"Bearer {still_valid}"}).status_code == 200
    assert expand(client, {"Authorization": f"Bearer {expired}"}).status_code == 401
