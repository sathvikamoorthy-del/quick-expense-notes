"""Fit: the module works with THIS app's scaffold glue files."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.http.app import create_app
from app.http.settings import Settings

GLUE = Path(__file__).resolve().parents[4] / "app" / "glue"


def test_glue_files_have_the_markers():
    for name in ("routes", "middleware", "providers", "config"):
        text = (GLUE / f"{name}.py").read_text()
        assert "# knm:imports" in text and "# knm:entries" in text and "# knm:entries-end" in text


def test_the_app_builds_from_the_real_glue_and_answers_404_in_the_envelope():
    client = TestClient(create_app(settings=Settings(env="production")))
    assert client.get("/nope").json() == {"error": "not-found"}
