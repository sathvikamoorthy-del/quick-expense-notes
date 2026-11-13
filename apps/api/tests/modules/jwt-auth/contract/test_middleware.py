import time

import jwt
import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from app.auth.jwt import AuthClaims
from app.auth.middleware import authenticate, current_auth, require_auth, require_role

SECRET = "s" * 40
ADMIN_ONLY = require_role("admin")  # define guards once at module level, then Depends(ADMIN_ONLY)


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)


def make():
    app = FastAPI()
    authenticate(app)

    @app.get("/open")
    def open_route(request: Request):
        auth = current_auth(request)
        return {"user": auth.user_id if auth else None}

    @app.get("/private")
    def private(auth: AuthClaims = Depends(require_auth)):
        return {"user": auth.user_id}

    @app.get("/admin")
    def admin(auth: AuthClaims = Depends(ADMIN_ONLY)):
        return {"user": auth.user_id}

    return TestClient(app)


def bearer(roles=None, secret=SECRET, **extra):
    body = {"sub": "u1", "exp": int(time.time()) + 3600, **({"roles": roles} if roles else {}), **extra}
    return {"Authorization": "Bearer " + jwt.encode(body, secret, algorithm="HS256")}


def test_no_header_is_anonymous_and_open_routes_work():
    r = make().get("/open")
    assert r.status_code == 200 and r.json() == {"user": None}


def test_a_valid_token_identifies_the_caller():
    assert make().get("/open", headers=bearer()).json() == {"user": "u1"}


def test_every_kind_of_bad_token_gets_the_same_401():
    client = make()
    bad_headers = [
        bearer(secret="x" * 40),
        bearer(exp=int(time.time()) - 5),
        {"Authorization": "Bearer not-a-token"},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer a b"},
    ]
    answers = {(r.status_code, r.text) for r in (client.get("/open", headers=h) for h in bad_headers)}
    assert answers == {(401, '{"error":"unauthorized"}')}


def test_other_authorization_schemes_are_anonymous():
    assert make().get("/open", headers={"Authorization": "Basic abc"}).json() == {"user": None}


def test_require_auth_is_401_for_anonymous_and_ok_with_a_token():
    client = make()
    assert client.get("/private").status_code == 401
    assert client.get("/private").json() == {
        "detail": "unauthorized"
    }  # the fastapi module's error handler turns detail into the envelope
    assert client.get("/private", headers=bearer()).json() == {"user": "u1"}


def test_require_role_is_401_then_403_then_ok():
    client = make()
    assert client.get("/admin").status_code == 401
    assert client.get("/admin", headers=bearer(roles=["staff"])).status_code == 403
    assert client.get("/admin", headers=bearer(roles=["admin"])).json() == {"user": "u1"}


def test_a_missing_secret_fails_closed_with_500_and_does_not_block_anonymous_calls(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "")
    client = make()
    r = client.get("/open", headers=bearer())
    assert r.status_code == 500 and r.json() == {"error": "auth-misconfigured"}
    assert client.get("/open").status_code == 200
