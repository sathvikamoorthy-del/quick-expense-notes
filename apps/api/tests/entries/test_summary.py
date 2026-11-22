"""REQ-279 / WI-049: the monthly summary, from a SQLite database built by the real migrations (0001-0004)."""

import sqlite3
import uuid
from datetime import date
from pathlib import Path

import pytest

from app.db.session import Database
from app.entries.summary import CATEGORY_ORDER, is_future, month_of, monthly_summary, parse_month
from tests.entries.test_codes import build_seeded_db

ASHA = "11111111-1111-1111-1111-111111111111"
RAVI = "22222222-2222-2222-2222-222222222222"
NAMES = {
    "F": "Food",
    "T": "Travel",
    "R": "Rent",
    "U": "Utilities",
    "S": "Shopping",
    "H": "Health",
    "E": "Entertainment",
    "O": "Other",
}

# The 8 working entries of 03-sample-entries.md as saved records (today = 12 Nov 2026)
SAMPLE = [
    ("F 250", "F", None, 25000, "2026-11-12"),
    ("SWG 340 yd", "F", "SWG", 34000, "2026-11-11"),
    ("UBR 180 12/11 airport", "T", "UBR", 18000, "2026-11-12"),
    ("R 1.5k", "R", None, 150000, "2026-11-12"),
    ("NFX 649", "E", "NFX", 64900, "2026-11-12"),
    ("APL 420 td fever tablets", "H", "APL", 42000, "2026-11-12"),
    ("S 2k td shoes", "S", None, 200000, "2026-11-12"),
    ("AMZ 799.50", "S", "AMZ", 79950, "2026-11-12"),
]


@pytest.fixture
def db_file(tmp_path: Path) -> Path:
    return build_seeded_db(tmp_path, users=(ASHA, RAVI))


def insert(db_file: Path, rows: list[tuple], user: str = ASHA) -> None:
    connection = sqlite3.connect(db_file)
    try:
        connection.executemany(
            "INSERT INTO expenses (id, user_id, typed_text, category_code, merchant_code, amount_paise, spent_on)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(str(uuid.uuid4()), user, *row) for row in rows],
        )
        connection.commit()
    finally:
        connection.close()


async def summary_of(db_file: Path, month: str, user: str = ASHA) -> list[tuple[str, int]]:
    """[(category, total_paise), ..., ("Grand total", paise)]"""
    bounds = parse_month(month)
    assert bounds is not None
    database = Database.from_url(f"file:{db_file}")
    try:
        async with database.sessions() as session:
            result = await monthly_summary(session, user, bounds[0], bounds[1], NAMES)
    finally:
        await database.dispose()
    return [(c.category, c.total_paise) for c in result.categories] + [("Grand total", result.grand_total_paise)]


async def test_the_sample_month_gives_the_req_279_totals_in_order(db_file):
    insert(db_file, SAMPLE)
    assert await summary_of(db_file, "2026-11") == [
        ("Food", 59000),
        ("Travel", 18000),
        ("Rent", 150000),
        ("Entertainment", 64900),
        ("Health", 42000),
        ("Shopping", 279950),
        ("Grand total", 613850),
    ]


async def test_utilities_and_other_come_last(db_file):
    insert(
        db_file,
        [
            ("O 5", "O", None, 500, "2026-11-01"),
            ("BSN 10", "U", "BSN", 1000, "2026-11-01"),
            ("F 1", "F", None, 100, "2026-11-01"),
        ],
    )
    assert [c for c, _ in await summary_of(db_file, "2026-11")] == ["Food", "Utilities", "Other", "Grand total"]


async def test_only_entries_dated_in_the_month_count(db_file):
    insert(
        db_file,
        [
            ("F 1", "F", None, 100, "2026-10-31"),
            ("F 2", "F", None, 200, "2026-11-01"),
            ("F 3", "F", None, 300, "2026-11-30"),
            ("F 4", "F", None, 400, "2026-12-01"),
        ],
    )
    assert await summary_of(db_file, "2026-11") == [("Food", 500), ("Grand total", 500)]
    assert await summary_of(db_file, "2026-10") == [("Food", 100), ("Grand total", 100)]
    assert await summary_of(db_file, "2026-12") == [("Food", 400), ("Grand total", 400)]


async def test_only_the_users_own_entries_count(db_file):
    insert(db_file, SAMPLE, user=ASHA)
    insert(db_file, [("R 9k", "R", None, 900000, "2026-11-05")], user=RAVI)
    assert (await summary_of(db_file, "2026-11", user=ASHA))[-1] == ("Grand total", 613850)
    assert await summary_of(db_file, "2026-11", user=RAVI) == [("Rent", 900000), ("Grand total", 900000)]


async def test_a_month_with_no_entries_is_empty(db_file):
    insert(db_file, SAMPLE)
    assert await summary_of(db_file, "2026-09") == [("Grand total", 0)]


def test_the_category_order_is_the_sample_then_utilities_and_other():
    assert [NAMES[c] for c in CATEGORY_ORDER] == [
        "Food",
        "Travel",
        "Rent",
        "Entertainment",
        "Health",
        "Shopping",
        "Utilities",
        "Other",
    ]


@pytest.mark.parametrize(
    ("text", "bounds"),
    [
        ("2026-11", (date(2026, 11, 1), date(2026, 12, 1))),
        ("2026-01", (date(2026, 1, 1), date(2026, 2, 1))),
        ("2026-12", (date(2026, 12, 1), date(2027, 1, 1))),
    ],
)
def test_parse_month(text, bounds):
    assert parse_month(text) == bounds


@pytest.mark.parametrize("text", ["2026-13", "2026-00", "2026-1", "26-11", "2026-11-01", "", "0000-01", "nov 2026"])
def test_parse_month_refuses_anything_else(text):
    assert parse_month(text) is None


def test_future_months_and_month_of():
    today = date(2026, 11, 30)
    assert not is_future(date(2026, 11, 1), today)
    assert not is_future(date(2025, 12, 1), today)
    assert is_future(date(2026, 12, 1), today)
    assert month_of(date(2026, 1, 5)) == "2026-01"
