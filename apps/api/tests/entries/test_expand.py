"""REQ-276 acceptance: every case of docs/requirements/REQ-276/req.md, with today = 12 Nov 2026 (IST)."""

from datetime import UTC, date, datetime

import pytest

from app.entries.clock import IST, today_ist
from app.entries.expand import (
    AMOUNT_DECIMALS,
    AMOUNT_MISSING,
    AMOUNT_NOT_POSITIVE,
    DATE_FUTURE,
    DATE_INVALID,
    CodeInfo,
    EntryError,
    Expanded,
    expand,
)

TODAY = date(2026, 11, 12)
YESTERDAY = date(2026, 11, 11)

# The code tables of docs/project/source/02-abbreviation-rules.md
CODES = {
    "F": CodeInfo(None, "Food"),
    "T": CodeInfo(None, "Travel"),
    "R": CodeInfo(None, "Rent"),
    "U": CodeInfo(None, "Utilities"),
    "S": CodeInfo(None, "Shopping"),
    "H": CodeInfo(None, "Health"),
    "E": CodeInfo(None, "Entertainment"),
    "O": CodeInfo(None, "Other"),
    "SWG": CodeInfo("Swiggy", "Food"),
    "ZMT": CodeInfo("Zomato", "Food"),
    "UBR": CodeInfo("Uber", "Travel"),
    "OLA": CodeInfo("Ola", "Travel"),
    "AMZ": CodeInfo("Amazon", "Shopping"),
    "NFX": CodeInfo("Netflix", "Entertainment"),
    "APL": CodeInfo("Apollo Pharmacy", "Health"),
    "BSN": CodeInfo("BSNL", "Utilities"),
}


def ok(text: str, today: date = TODAY) -> Expanded:
    result = expand(text, today, CODES)
    assert isinstance(result, Expanded), result
    return result


def error(text: str, today: date = TODAY) -> str:
    result = expand(text, today, CODES)
    assert isinstance(result, EntryError), result
    return result.message


# (typed, merchant, category, amount, date, note) - 03-sample-entries.md "Entries that work"
WORKING = [
    ("F 250", None, "Food", "250.00", TODAY, None),
    ("SWG 340 yd", "Swiggy", "Food", "340.00", YESTERDAY, None),
    ("UBR 180 12/11 airport", "Uber", "Travel", "180.00", TODAY, "airport"),
    ("R 1.5k", None, "Rent", "1500.00", TODAY, None),
    ("NFX 649", "Netflix", "Entertainment", "649.00", TODAY, None),
    ("APL 420 td fever tablets", "Apollo Pharmacy", "Health", "420.00", TODAY, "fever tablets"),
    ("S 2k td shoes", None, "Shopping", "2000.00", TODAY, "shoes"),
    ("AMZ 799.50", "Amazon", "Shopping", "799.50", TODAY, None),
]


@pytest.mark.parametrize(("typed", "merchant", "category", "amount", "day", "note"), WORKING)
def test_sample_entries_that_work(typed, merchant, category, amount, day, note):
    result = ok(typed)
    assert (result.merchant, result.category, result.amount, result.date, result.note) == (
        merchant,
        category,
        amount,
        day,
        note,
    )


@pytest.mark.parametrize(
    ("typed", "message"),
    [
        ("X 100", 'Unknown code "X".'),
        ("F", AMOUNT_MISSING),
        ("F -50", AMOUNT_NOT_POSITIVE),
        ("F 100 32/13", DATE_INVALID),
        ("F 100 20/11", DATE_FUTURE),
    ],
)
def test_sample_entries_that_fail(typed, message):
    assert error(typed) == message


def test_amount_in_paise_and_code_in_upper_case():
    result = ok("swg 340")
    assert (result.code, result.merchant, result.category, result.amount_paise, result.date) == (
        "SWG",
        "Swiggy",
        "Food",
        34000,
        TODAY,
    )
    assert ok("AMZ 799.50").amount_paise == 79950


def test_case_insensitive_date_words_and_k_suffix():
    result = ok("F 1.5K YD")
    assert (result.merchant, result.category, result.amount, result.date) == (None, "Food", "1500.00", YESTERDAY)
    assert ok("f 2k Td").date == TODAY


def test_day_and_month_without_leading_zero():
    assert ok("F 100 5/11").date == date(2026, 11, 5)
    assert ok("F 100 05/11").date == date(2026, 11, 5)
    assert ok("F 100 12/1").date == date(2026, 1, 12)


def test_extra_spaces_between_fields_and_around_the_entry():
    assert ok("  SWG   340   yd  ") == ok("SWG 340 yd")
    assert ok("APL  420  td   fever tablets ").note == "fever tablets"


def test_note_keeps_its_inner_spaces():
    assert ok("APL 420 td fever  tablets").note == "fever  tablets"
    assert ok("F 250 lunch with  team").note == "lunch with  team"


@pytest.mark.parametrize("typed", ["F 250.555", "F 1.2345k"])
def test_more_than_two_decimals_counted_as_typed(typed):
    assert error(typed) == AMOUNT_DECIMALS


def test_greater_than_zero_is_checked_before_the_decimals():
    assert error("F -1.555") == AMOUNT_NOT_POSITIVE


def test_checks_run_in_the_order_of_the_error_table():
    assert error("X -1 32/13") == 'Unknown code "X".'
    assert error("F 0 32/13") == AMOUNT_NOT_POSITIVE
    assert error("F 1.555 32/13") == AMOUNT_DECIMALS
    assert error("F 100 31/2") == DATE_INVALID


def test_unknown_code_is_shown_as_typed():
    assert error("xyz 100") == 'Unknown code "xyz".'


@pytest.mark.parametrize("amount", ["0", "0.00", "abc", "k", "1.5x", "-0.5k", "1e3", "NaN"])
def test_zero_negative_or_not_a_number(amount):
    assert error(f"F {amount}") == AMOUNT_NOT_POSITIVE


@pytest.mark.parametrize("token", ["00/11", "31/11", "29/2", "1/13", "123/4", "1/0"])
def test_dates_that_are_not_real(token):
    assert error(f"F 100 {token}") == DATE_INVALID


def test_a_word_that_is_not_date_shaped_starts_the_note():
    result = ok("F 250 lunch")
    assert (result.date, result.note) == (TODAY, "lunch")


def test_an_empty_entry_is_not_a_rule_case():
    with pytest.raises(ValueError):
        expand("   ", TODAY, CODES)


def test_today_follows_ist_at_midnight():
    # 00:30 IST on 13 Nov 2026 is 19:00 UTC on 12 Nov: "td" is the 13th whatever the server's own time zone.
    now = datetime(2026, 11, 12, 19, 0, tzinfo=UTC)
    today = today_ist(now)
    assert today == date(2026, 11, 13)
    assert ok("F 100 td", today=today).date == date(2026, 11, 13)
    assert ok("F 100 13/11", today=today).date == date(2026, 11, 13)


def test_today_ist_default_is_an_ist_date():
    assert today_ist() == datetime.now(IST).date()
