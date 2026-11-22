"""The code table, read from a SQLite database built by the real migrations (schema 0001 + seed 0002)."""

import sqlite3
from pathlib import Path

import pytest

from app.db.session import Database
from app.entries.codes import clear_codes_cache, load_codes, read_codes
from app.entries.expand import CodeInfo

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def build_seeded_db(directory: Path, users: tuple[str, ...] = ()) -> Path:
    """A database file built by every migration (categories and merchants with their 16 seed rows, users, expenses),
    plus one users row per given id (also used by test_routes and test_save)."""
    path = directory / "app.db"
    connection = sqlite3.connect(path)
    try:
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            connection.executescript(migration.read_text(encoding="utf-8"))
        for user_id in users:
            connection.execute(
                "INSERT INTO users (id, email, password_hash, display_name) VALUES (?, ?, 'x', 'Tester')",
                (user_id, f"{user_id}@example.com"),
            )
        connection.commit()
    finally:
        connection.close()
    return path


@pytest.fixture
def seeded_db_file(tmp_path: Path) -> Path:
    return build_seeded_db(tmp_path)


@pytest.fixture(autouse=True)
def fresh_codes_cache():
    clear_codes_cache()
    yield
    clear_codes_cache()


async def test_reads_the_seeded_categories_and_merchants(seeded_db_file):
    database = Database.from_url(f"file:{seeded_db_file}")
    try:
        async with database.sessions() as session:
            codes = await read_codes(session)
    finally:
        await database.dispose()
    assert len(codes) == 16
    assert codes["F"] == CodeInfo(None, "Food", "F")
    assert codes["O"] == CodeInfo(None, "Other", "O")
    assert codes["SWG"] == CodeInfo("Swiggy", "Food", "F")  # a merchant code carries its category's code
    assert codes["APL"] == CodeInfo("Apollo Pharmacy", "Health", "H")
    assert codes["BSN"] == CodeInfo("BSNL", "Utilities", "U")


async def test_the_table_is_read_once_and_cached(seeded_db_file):
    database = Database.from_url(f"file:{seeded_db_file}")
    try:
        async with database.sessions() as session:
            first = await load_codes(session)
        await database.dispose()
        database = Database.from_url("file::memory:")  # no tables: a second read would fail
        async with database.sessions() as session:
            assert await load_codes(session) is first
    finally:
        await database.dispose()
