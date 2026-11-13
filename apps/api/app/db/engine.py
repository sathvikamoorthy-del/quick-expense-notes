"""Async SQLAlchemy engine from DATABASE_URL (local SQLite through aiosqlite)."""

import os
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./data/app.db"


def normalize_url(url: str) -> str:
    """Accepts file:./x.db, sqlite:///x.db, sqlite+aiosqlite:///x.db and :memory:; returns an async SQLite URL."""
    raw = url.strip()
    if raw == ":memory:" or raw == "file::memory:":
        return "sqlite+aiosqlite:///:memory:"
    if raw.startswith("file:"):
        return "sqlite+aiosqlite:///" + raw[len("file:") :].split("?")[0]
    if raw.startswith("sqlite+aiosqlite:"):
        return raw
    if raw.startswith("sqlite:"):
        return "sqlite+aiosqlite:" + raw[len("sqlite:") :]
    if raw.startswith(("libsql:", "sqlite+libsql:", "sqlite+aiolibsql:", "https:", "wss:")):
        raise ValueError("Turso (libsql) is not supported by the async engine yet: use a local SQLite URL")
    scheme = raw.split(":", 1)[0][:20]  # never echo the rest of the URL: it may hold a password
    raise ValueError(f'unsupported database URL scheme "{scheme}": use file:./x.db, sqlite:///x.db or :memory:')


def database_url() -> str:
    return os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL


def _sqlite_file(url: str) -> Path | None:
    prefix = "sqlite+aiosqlite:///"
    path = url[len(prefix) :].split("?")[0] if url.startswith(prefix) else ""
    return None if path in ("", ":memory:") else Path(path)


def create_engine(url: str | None = None, **kwargs: Any) -> AsyncEngine:
    resolved = normalize_url(url if url is not None else database_url())
    file = _sqlite_file(resolved)
    if file is not None:
        file.resolve().parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(resolved, **kwargs)

    @event.listens_for(engine.sync_engine, "connect")
    def _foreign_keys(dbapi_connection: Any, _record: Any) -> None:  # SQLite ignores foreign keys unless asked
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine
