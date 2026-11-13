"""Fit: the middleware is registered in THIS app's glue and works through create_app."""

import time
from pathlib import Path

import jwt
from fastapi import Depends
from fastapi.testclient import TestClient

from app.auth.jwt import AuthClaims
from app.auth.middleware import require_auth
from app.http.app import create_app
from app.http.settings import Settings

GLUE = Path(__file__).resolve().parents[4] / "app" / "glue"


def test_authenticate_is_registered_in_the_middleware_glue():
    text = (GLUE / "middleware.py").read_text()
    assert "authenticate" in text and "# knm:module jwt-auth" in text


def test_the_app_built_from_the_real_glue_authenticates(monkeypatch):
    secret = "k" * 40
    monkeypatch.setenv("JWT_SECRET", secret)
    app = create_app(settings=Settings(env="production"))

    @app.get("/me")
    def me(auth: AuthClaims = Depends(require_auth)):
        return {"user": auth.user_id}

    client = TestClient(app)
    anonymous = client.get("/me")
    assert anonymous.status_code == 401
    assert anonymous.json() == {"error": "unauthorized"}
    token = jwt.encode({"sub": "u7", "exp": int(time.time()) + 60}, secret, algorithm="HS256")
    assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).json() == {"user": "u7"}
