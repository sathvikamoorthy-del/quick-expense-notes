"""REQ-280 / WI-052: the saved-entries list and editing a saved entry, on a database built from migrations 0001-0004."""

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from app.db.session import Database
from app.entries.edit import ONE_ENTRY_ONLY, Refused, edit_entry, list_month, saved_day
from app.entries.summary import monthly_summary, parse_month
from tests.entries.test_codes import build_seeded_db
from tests.entries.test_expand import CODES, TODAY

ASHA = "11111111-1111-1111-1111-111111111111"
RAVI = "22222222-2222-2222-2222-222222222222"
# Saved on 12 Nov 2026 at 10:00 IST (04:30 UTC)
SAVED_12_NOV = "2026-11-12T04:30:00.000Z"
NAMES = {info.category_code: info.category for info in CODES.values()}

ROW = tuple[
    str, str, str | None, str, int, str, str | None, str
]  # id, typed, merchant, category, paise, date, note, created


def ident(n: int) -> str:
    return f"00000000-0000-0000-0000-{n:012d}"


@pytest.fixture
def db_file(tmp_path: Path) -> Path:
    return build_seeded_db(tmp_path, users=(ASHA, RAVI))


@pytest.fixture
async def database(db_file: Path):
    db = Database.from_url(f"file:{db_file}")
    yield db
    await db.dispose()


def insert(db_file: Path, rows: list[ROW], user: str = ASHA) -> None:
    connection = sqlite3.connect(db_file)
    try:
        for expense_id, typed, merchant, category, paise, spent_on, note, created in rows:
            connection.execute(
                "INSERT INTO expenses (id, user_id, typed_text, merchant_code, category_code, amount_paise, spent_on,"
                " note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (expense_id, user, typed, merchant, category, paise, spent_on, note, created, created),
            )
        connection.commit()
    finally:
        connection.close()


def stored(db_file: Path, expense_id: str) -> tuple:
    connection = sqlite3.connect(db_file)
    try:
        return connection.execute(
            "SELECT typed_text, merchant_code, category_code, amount_paise, spent_on, note, created_at, updated_at,"
            " user_id FROM expenses WHERE id = ?",
            (expense_id,),
        ).fetchone()
    finally:
        connection.close()


async def edit(database: Database, expense_id: str, text: str, user: str = ASHA, today: date = TODAY):
    async with database.sessions() as session:
        outcome = await edit_entry(session, user, expense_id, text, today, CODES)
        await session.commit()
    return outcome


UBR: ROW = (ident(1), "UBR 180 12/11 airport", "UBR", "T", 18000, "2026-11-12", "airport", SAVED_12_NOV)
SWG: ROW = (ident(2), "SWG 340 yd", "SWG", "F", 34000, "2026-11-11", None, SAVED_12_NOV)


async def test_an_edit_replaces_the_entry_in_place(database, db_file):
    insert(db_file, [UBR])
    outcome = await edit(database, ident(1), "UBR 220 12/11 airport")
    assert not isinstance(outcome, Refused) and outcome is not None
    typed, merchant, category, paise, spent_on, note, created, updated, owner = stored(db_file, ident(1))
    assert (typed, merchant, category, paise, spent_on, note) == (
        "UBR 220 12/11 airport",
        "UBR",
        "T",
        22000,
        "2026-11-12",
        "airport",
    )
    assert (created, owner) == (SAVED_12_NOV, ASHA)
    assert updated > created and updated.endswith("Z")
    assert outcome.amount_paise == 22000 and outcome.id == ident(1)


async def test_re_saving_the_pre_filled_yd_entry_a_week_later_keeps_its_date(database, db_file):
    insert(db_file, [SWG])
    await edit(database, ident(2), "SWG 360 yd", today=date(2026, 11, 19))
    assert stored(db_file, ident(2))[3:5] == (36000, "2026-11-11")


async def test_no_date_and_td_mean_the_saved_day(database, db_file):
    insert(db_file, [SWG])
    await edit(database, ident(2), "F 99", today=date(2026, 11, 19))
    assert stored(db_file, ident(2))[4] == "2026-11-12"


async def test_the_future_check_uses_today(database, db_file):
    saved_5_nov = (ident(3), "F 100", None, "F", 10000, "2026-11-05", None, "2026-11-05T04:30:00.000Z")
    insert(db_file, [saved_5_nov])
    assert not isinstance(await edit(database, ident(3), "F 100 10/11"), Refused)  # 10 Nov: after 5 Nov, before today
    assert stored(db_file, ident(3))[4] == "2026-11-10"
    assert await edit(database, ident(3), "F 100 20/11") == Refused("Date cannot be in the future.")
    assert stored(db_file, ident(3))[4] == "2026-11-10"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("X 100", 'Unknown code "X".'),
        ("F", "Amount is missing."),
        ("F -5", "Amount must be greater than 0."),
        ("F 1.555", "Amount must have at most 2 decimals."),
        ("F 100 32/13", "Date is not valid."),
        ("F 1; F 2", ONE_ENTRY_ONLY),
        ("F 1\nF 2", ONE_ENTRY_ONLY),
    ],
)
async def test_an_invalid_edit_is_refused_with_the_rule_message_and_changes_nothing(database, db_file, text, message):
    insert(db_file, [UBR])
    before = stored(db_file, ident(1))
    assert await edit(database, ident(1), text) == Refused(message)
    assert stored(db_file, ident(1)) == before


async def test_a_category_code_becomes_a_merchant_code_and_back(database, db_file):
    insert(db_file, [(ident(4), "F 250", None, "F", 25000, "2026-11-12", None, SAVED_12_NOV)])
    await edit(database, ident(4), "AMZ 250")
    assert stored(db_file, ident(4))[1:3] == ("AMZ", "S")
    await edit(database, ident(4), "T 250 cab")
    assert stored(db_file, ident(4))[1:3] + stored(db_file, ident(4))[5:6] == (None, "T", "cab")


async def test_another_users_entry_or_an_unknown_id_is_not_found(database, db_file):
    insert(db_file, [UBR], user=RAVI)
    before = stored(db_file, ident(1))
    assert await edit(database, ident(1), "UBR 1", user=ASHA) is None
    assert await edit(database, ident(99), "UBR 1", user=ASHA) is None
    assert stored(db_file, ident(1)) == before


async def test_the_list_shows_the_users_month_newest_date_first(database, db_file):
    insert(
        db_file,
        [
            (ident(10), "F 1 31/10", None, "F", 100, "2026-10-31", None, "2026-11-01T04:30:00.000Z"),
            (ident(11), "F 2 1/11", None, "F", 200, "2026-11-01", None, "2026-11-01T04:30:00.000Z"),
            (ident(12), "F 3", None, "F", 300, "2026-11-12", None, "2026-11-12T04:30:00.000Z"),
            (ident(13), "F 4", None, "F", 400, "2026-11-12", None, "2026-11-12T05:30:00.000Z"),  # saved later
            (ident(14), "F 5 1/12", None, "F", 500, "2026-12-01", None, "2026-12-01T04:30:00.000Z"),
        ],
    )
    insert(db_file, [(ident(20), "R 9k", None, "R", 900000, "2026-11-05", None, SAVED_12_NOV)], user=RAVI)
    start, end = parse_month("2026-11")
    async with database.sessions() as session:
        rows = await list_month(session, ASHA, start, end)
    assert [r.typed_text for r in rows] == ["F 4", "F 3", "F 2 1/11"]


async def test_the_summary_follows_an_edit_that_moves_the_entry_to_another_month(database, db_file):
    insert(db_file, [UBR, SWG])

    async def total(month: str) -> int:
        start, end = parse_month(month)
        async with database.sessions() as session:
            return (await monthly_summary(session, ASHA, start, end, NAMES)).grand_total_paise

    assert (await total("2026-11"), await total("2026-10")) == (52000, 0)
    await edit(database, ident(1), "UBR 180 30/10 airport")
    assert (await total("2026-11"), await total("2026-10")) == (34000, 18000)


@pytest.mark.parametrize(
    ("created_at", "day"),
    [
        ("2026-11-12T04:30:00.000Z", date(2026, 11, 12)),
        ("2026-11-12T19:00:00.000Z", date(2026, 11, 13)),  # 00:30 IST on 13 Nov
        ("2026-11-12T18:29:59.999Z", date(2026, 11, 12)),  # 23:59 IST on 12 Nov
    ],
)
def test_the_saved_day_is_the_ist_date_of_created_at(created_at, day):
    assert saved_day(created_at) == day
