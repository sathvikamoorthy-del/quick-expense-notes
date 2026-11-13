import pytest
from sqlalchemy import text

from app.db.engine import DEFAULT_DATABASE_URL, create_engine, database_url, normalize_url


def test_normalizes_file_sqlite_and_memory_urls():
    assert normalize_url("file:./data/app.db") == "sqlite+aiosqlite:///./data/app.db"
    assert normalize_url("file:./x.db?mode=rwc") == "sqlite+aiosqlite:///./x.db"
    assert normalize_url("sqlite:///x.db") == "sqlite+aiosqlite:///x.db"
    assert normalize_url("sqlite+aiosqlite:///x.db") == "sqlite+aiosqlite:///x.db"
    assert normalize_url(":memory:") == "sqlite+aiosqlite:///:memory:"


def test_turso_is_refused_with_a_clear_message():
    with pytest.raises(ValueError, match="Turso"):
        normalize_url("libsql://my-db.turso.io")


def test_unknown_schemes_are_refused_without_echoing_the_whole_url():
    with pytest.raises(ValueError, match="unsupported database URL"):
        normalize_url("postgresql://user:secret@host/db")
    try:
        normalize_url("postgresql://user:secret-password@host/db")
    except ValueError as err:
        assert "secret-password" not in str(err)


def test_database_url_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert database_url() == DEFAULT_DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", "file:./other.db")
    assert database_url() == "file:./other.db"


async def test_creates_the_folder_of_a_file_database_and_turns_foreign_keys_on(tmp_path):
    engine = create_engine(f"file:{tmp_path}/nested/dir/app.db")
    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text("PRAGMA foreign_keys"))).scalar() == 1
        assert (tmp_path / "nested" / "dir" / "app.db").exists()
    finally:
        await engine.dispose()
