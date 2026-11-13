"""The code table, read from a SQLite database built by the real migrations (schema 0001 + seed 0002)."""

import sqlite3
from pathlib import Path

import pytest

from app.db.session import Database
from app.entries.codes import clear_codes_cache, load_codes, read_codes
from app.entries.expand import CodeInfo

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def build_seeded_db(directory: Path) -> Path:
    """A database file with the categories and merchants tables and their 16 seed rows (also used by test_routes)."""
    path = directory / "app.db"
    connection = sqlite3.connect(path)
    try:
        for name in ("0001_db_design.sql", "0002_seed_reference.sql"):
            connection.executescript((MIGRATIONS / name).read_text(encoding="utf-8"))
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
    assert codes["F"] == CodeInfo(None, "Food")
    assert codes["O"] == CodeInfo(None, "Other")
    assert codes["SWG"] == CodeInfo("Swiggy", "Food")
    assert codes["APL"] == CodeInfo("Apollo Pharmacy", "Health")
    assert codes["BSN"] == CodeInfo("BSNL", "Utilities")


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
