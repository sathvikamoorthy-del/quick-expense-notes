from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.provider import database_provider
from app.db.session import Database


def test_the_provider_puts_one_database_on_the_app(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"file:{tmp_path}/p.db")
    app = FastAPI()
    database = database_provider(app)
    assert isinstance(database, Database)
    assert app.state.db is database


def test_the_engine_is_disposed_at_shutdown_and_the_original_lifespan_still_runs(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"file:{tmp_path}/p.db")
    events: list[str] = []
    app = FastAPI()
    database = database_provider(app)

    async def spy() -> None:
        events.append("disposed")

    database.dispose = spy  # type: ignore[method-assign]
    with TestClient(app):
        assert events == []
    assert events == ["disposed"]
