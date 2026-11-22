"""REQ-278 / WI-048: saving reviewed entries, against a SQLite database built by the real migrations (0001-0004)."""

import sqlite3
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.session import Database
from app.entries.batch import expand_all
from app.entries.save import REVIEW_CHANGED, Refused, Reviewed, Saved, UnknownUser, as_reviewed, save_reviewed
from app.models import Expenses
from tests.entries.test_codes import build_seeded_db
from tests.entries.test_expand import CODES, TODAY

ASHA = "11111111-1111-1111-1111-111111111111"
RAVI = "22222222-2222-2222-2222-222222222222"
SAMPLE = "F 250; SWG 340 yd\nX 100\nUBR 180 12/11 airport"


def review(text: str, today: date = TODAY) -> list[Reviewed]:
    """What /entries/expand-all showed the user."""
    results = expand_all(text, today, CODES)
    assert isinstance(results, list)
    return [as_reviewed(item) for item in results]


@pytest.fixture
def db_file(tmp_path: Path) -> Path:
    return build_seeded_db(tmp_path, users=(ASHA, RAVI))


@pytest.fixture
async def database(db_file: Path):
    db = Database.from_url(f"file:{db_file}")
    yield db
    await db.dispose()


async def save(database: Database, text: str, reviewed: list[Reviewed], user: str = ASHA, today: date = TODAY):
    async with database.sessions() as session:
        outcome = await save_reviewed(session, user, text, reviewed, today, CODES)
        await session.commit()
    return outcome


async def rows(database: Database, user: str = ASHA) -> list[tuple]:
    async with database.sessions() as session:
        query = select(
            Expenses.typed_text,
            Expenses.merchant_code,
            Expenses.category_code,
            Expenses.amount_paise,
            Expenses.spent_on,
            Expenses.note,
        ).where(Expenses.user_id == user)
        return sorted((await session.execute(query)).all())


async def test_the_sample_saves_three_entries_exactly_as_reviewed_and_not_x_100(database):
    outcome = await save(database, SAMPLE, review(SAMPLE))
    assert isinstance(outcome, Saved)
    assert len(outcome.ids) == 3 and all(len(i) == 36 for i in outcome.ids)
    assert [(f.typed, f.result.message) for f in outcome.failed] == [("X 100", 'Unknown code "X".')]
    assert await rows(database) == [
        ("F 250", None, "F", 25000, "2026-11-12", None),
        ("SWG 340 yd", "SWG", "F", 34000, "2026-11-11", None),
        ("UBR 180 12/11 airport", "UBR", "T", 18000, "2026-11-12", "airport"),
    ]


async def test_timestamps_are_set_by_the_database(database, db_file):
    await save(database, "F 250", review("F 250"))
    connection = sqlite3.connect(db_file)
    try:
        created, updated = connection.execute("SELECT created_at, updated_at FROM expenses").fetchone()
    finally:
        connection.close()
    assert created == updated and created.endswith("Z") and "T" in created


@pytest.mark.parametrize(
    "change",
    [
        lambda r: [replace(r[0], amount_paise=26000), *r[1:]],  # another amount
        lambda r: [replace(r[0], date=date(2026, 11, 10)), *r[1:]],  # another date
        lambda r: [replace(r[0], note="lunch"), *r[1:]],  # another note
        lambda r: r[:-1],  # one entry left out
        lambda r: [r[1], r[0], *r[2:]],  # another order
        lambda r: [*r[:2], replace(r[2], error="Amount is missing."), r[3]],  # another error
    ],
)
async def test_a_review_that_differs_saves_nothing(database, change):
    assert await save(database, SAMPLE, change(review(SAMPLE))) == Refused(REVIEW_CHANGED)
    assert await rows(database) == []


async def test_a_review_made_before_midnight_is_refused_after_it(database):
    reviewed = review("SWG 340 yd\nF 100 td", today=date(2026, 11, 12))
    outcome = await save(database, "SWG 340 yd\nF 100 td", reviewed, today=date(2026, 11, 13))
    assert outcome == Refused(REVIEW_CHANGED)
    assert await rows(database) == []


async def test_too_many_entries_at_save_time_saves_nothing(database):
    text = "\n".join(["F 1"] * 21)
    assert await save(database, text, []) == Refused("Too many entries (max 20).")
    assert await rows(database) == []


async def test_saving_the_same_text_twice_creates_duplicates(database):
    await save(database, SAMPLE, review(SAMPLE))
    await save(database, SAMPLE, review(SAMPLE))
    assert len(await rows(database)) == 6


async def test_records_belong_to_the_signed_in_user_only(database):
    await save(database, "F 250", review("F 250"), user=ASHA)
    await save(database, "R 1.5k", review("R 1.5k"), user=RAVI)
    assert [r[0] for r in await rows(database, ASHA)] == ["F 250"]
    assert [r[0] for r in await rows(database, RAVI)] == ["R 1.5k"]


async def test_a_review_with_only_errors_saves_nothing(database):
    outcome = await save(database, "X 1; F", review("X 1; F"))
    assert isinstance(outcome, Saved) and outcome.ids == []
    assert [f.typed for f in outcome.failed] == ["X 1", "F"]
    assert await rows(database) == []


async def test_a_user_with_no_users_row_is_refused(database):
    with pytest.raises(UnknownUser):
        await save(database, "F 250", review("F 250"), user="33333333-3333-3333-3333-333333333333")
    assert await rows(database, "33333333-3333-3333-3333-333333333333") == []


# The migration's constraints (foreign keys on, as on every app connection)
def insert(db_file: Path, user=ASHA, category="F", merchant=None, amount=25000, spent_on="2026-11-12") -> None:
    connection = sqlite3.connect(db_file)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO expenses (id, user_id, typed_text, category_code, merchant_code, amount_paise, spent_on)"
            " VALUES (lower(hex(randomblob(18))), ?, 'typed', ?, ?, ?, ?)",
            (user, category, merchant, amount, spent_on),
        )
        connection.commit()
    finally:
        connection.close()


def test_the_migration_accepts_a_valid_row(db_file):
    insert(db_file, category="F", merchant="SWG")
    insert(db_file, category="F", merchant=None)


@pytest.mark.parametrize(
    "bad",
    [
        {"category": "T", "merchant": "SWG"},  # a merchant with another category
        {"category": "Z"},  # unknown category
        {"amount": 0},
        {"amount": 1.5},
        {"spent_on": "2026-02-30"},
        {"spent_on": "12/11/2026"},
        {"user": "44444444-4444-4444-4444-444444444444"},  # unknown user
    ],
)
def test_the_migration_rejects_bad_rows(db_file, bad):
    with pytest.raises(sqlite3.IntegrityError):
        insert(db_file, **bad)


def test_deleting_a_user_deletes_their_expenses(db_file):
    insert(db_file)
    connection = sqlite3.connect(db_file)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("DELETE FROM users WHERE id = ?", (ASHA,))
        connection.commit()
        assert connection.execute("SELECT count(*) FROM expenses").fetchone() == (0,)
    finally:
        connection.close()
