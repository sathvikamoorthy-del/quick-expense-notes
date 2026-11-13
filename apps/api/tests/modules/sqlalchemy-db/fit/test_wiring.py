"""Fit: the module is registered in THIS app's glue and works through create_app."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Note
from app.http.app import create_app
from app.http.settings import Settings

GLUE = Path(__file__).resolve().parents[4] / "app" / "glue"


def test_the_provider_is_registered_in_the_providers_glue():
    text = (GLUE / "providers.py").read_text()
    assert "database_provider" in text and "# knm:module sqlalchemy-db" in text


def test_the_config_glue_has_the_database_url_key():
    assert '"key": "DATABASE_URL"' in (GLUE / "config.py").read_text()


def test_the_app_built_from_the_real_glue_has_a_working_database(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"file:{tmp_path}/fit.db")
    app = create_app(settings=Settings(env="production"))
    with TestClient(app):
        pass
    assert app.state.db is not None
    assert select(Note) is not None
