"""Fit: the module is registered in THIS app's glue and the TTL comes from the environment."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.cache.middleware import CacheSettings
from app.http.app import create_app
from app.http.settings import Settings

GLUE = Path(__file__).resolve().parents[4] / "app" / "glue"


def test_the_cache_middleware_is_registered_and_the_ttl_key_is_in_the_config_glue():
    assert "cache_middleware" in (GLUE / "middleware.py").read_text()
    assert '"key": "CACHE_TTL_SECONDS"' in (GLUE / "config.py").read_text()


def test_the_ttl_defaults_to_30_seconds_and_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv("CACHE_TTL_SECONDS", raising=False)
    assert CacheSettings().cache_ttl_seconds == 30
    monkeypatch.setenv("CACHE_TTL_SECONDS", "5")
    assert CacheSettings().cache_ttl_seconds == 5


def test_a_repeated_get_through_the_real_glue_is_cached():
    app = create_app(settings=Settings(env="production"))
    calls = {"n": 0}

    @app.get("/count")
    def count():
        calls["n"] += 1
        return {"n": calls["n"]}

    client = TestClient(app)
    assert client.get("/count").json() == client.get("/count").json() == {"n": 1}
