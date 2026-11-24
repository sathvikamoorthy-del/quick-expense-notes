"""REQ-438 / WI-066: which lines go to AI and the rule check of an AI answer, with today = 12 Nov 2026 (IST)."""

from datetime import date

import pytest

from app.entries.ai_read import (
    AI_UNREADABLE,
    AiAnswer,
    AiFailure,
    check_answer,
    is_code_form,
)
from app.entries.expand import CodeInfo, EntryError, Expanded
from tests.entries.test_expand import CODES, TODAY, YESTERDAY

SENTENCE = "paid 450 to zomato yesterday for dinner"


def zomato_answer(**changes: object) -> AiAnswer:
    """What the AI answers for SENTENCE on 12 Nov 2026."""
    values: dict[str, object] = {
        "readable": True,
        "merchant_code": "ZMT",
        "other_merchant": None,
        "category_code": None,
        "amount": "450",
        "date": "2026-11-11",
        "note": "dinner",
    }
    values.update(changes)
    return AiAnswer.model_validate(values)


class FakeReader:
    """A reader that answers from a table (unknown lines are unreadable) and records the lines it was asked."""

    def __init__(self, answers: dict[str, AiAnswer | AiFailure]) -> None:
        self.answers = answers
        self.calls: list[str] = []

    async def read(self, line: str, today: date, codes: dict[str, CodeInfo]) -> AiAnswer | AiFailure:
        self.calls.append(line)
        return self.answers.get(line, AiFailure.UNREADABLE)


@pytest.mark.parametrize(
    "line", ["X 100", "F", "F -50", "F abc", "F 100 32/13", "swg 340 yd", "SWG 340", "  ola 90  ", "F\t250"]
)
def test_lines_whose_first_word_is_one_to_three_letters_are_code_form(line):
    assert is_code_form(line)


@pytest.mark.parametrize("line", [SENTENCE, "Uber 180", "450 zomato", "spent 200 on groceries", "F1 100", "₹450 tea"])
def test_every_other_line_goes_to_ai(line):
    assert not is_code_form(line)


def test_the_sample_sentence_becomes_zomato_food_450_yesterday_dinner():
    entry = check_answer(zomato_answer(), TODAY, CODES)
    assert entry == Expanded(
        code="ZMT",
        merchant="Zomato",
        category="Food",
        category_code="F",
        amount_paise=45000,
        date=YESTERDAY,
        note="dinner",
    )


def test_a_category_answer_has_no_merchant_and_codes_are_not_case_sensitive():
    entry = check_answer(zomato_answer(merchant_code=None, category_code="f", note=" groceries "), TODAY, CODES)
    assert isinstance(entry, Expanded)
    assert (entry.code, entry.merchant, entry.category, entry.note) == ("F", None, "Food", "groceries")


def test_a_merchant_sets_its_category_whatever_category_the_ai_gave():
    entry = check_answer(zomato_answer(category_code="S"), TODAY, CODES)
    assert isinstance(entry, Expanded) and (entry.category, entry.category_code) == ("Food", "F")


@pytest.mark.parametrize(
    "changes",
    [
        {"readable": False},
        {"merchant_code": None, "other_merchant": "Dominos", "category_code": "F"},
        {"merchant_code": "DOM"},
        {"merchant_code": "F"},  # a category code is not a merchant
        {"merchant_code": None, "category_code": "ZMT"},  # a merchant code is not a category
        {"merchant_code": None, "category_code": "Q"},
        {"merchant_code": None, "category_code": None},
    ],
)
def test_an_unknown_merchant_or_category_or_an_unreadable_line_is_an_error(changes):
    assert check_answer(zomato_answer(**changes), TODAY, CODES) == EntryError(AI_UNREADABLE)


@pytest.mark.parametrize(
    ("amount", "error"),
    [
        ("0", "Amount must be greater than 0."),
        ("-5", "Amount must be greater than 0."),
        ("", "Amount must be greater than 0."),
        ("four fifty", "Amount must be greater than 0."),
        ("4.505", "Amount must have at most 2 decimals."),
    ],
)
def test_the_amount_follows_the_rules(amount, error):
    assert check_answer(zomato_answer(amount=amount), TODAY, CODES) == EntryError(error)


@pytest.mark.parametrize(("amount", "paise"), [("1.5k", 150000), ("799.50", 79950), (" 450 ", 45000)])
def test_valid_amounts_are_stored_in_paise(amount, paise):
    entry = check_answer(zomato_answer(amount=amount), TODAY, CODES)
    assert isinstance(entry, Expanded) and entry.amount_paise == paise


@pytest.mark.parametrize(
    ("day", "error"),
    [
        ("2026-11-13", "Date cannot be in the future."),
        ("2025-12-31", "Date is not valid."),  # before 1 January of the current year (WI-066 q2)
        ("yesterday", "Date is not valid."),
        ("2026-02-30", "Date is not valid."),
    ],
)
def test_the_date_must_lie_between_1_january_and_today(day, error):
    assert check_answer(zomato_answer(date=day), TODAY, CODES) == EntryError(error)


@pytest.mark.parametrize("day", ["2026-01-01", "2026-11-12"])
def test_1_january_and_today_are_allowed(day):
    entry = check_answer(zomato_answer(date=day), TODAY, CODES)
    assert isinstance(entry, Expanded) and entry.date == date.fromisoformat(day)


@pytest.mark.parametrize(("note", "expected"), [(None, None), ("  ", None), ("tea; snacks\nlate", "tea snacks late")])
def test_a_note_never_holds_an_entry_separator(note, expected):
    entry = check_answer(zomato_answer(note=note), TODAY, CODES)
    assert isinstance(entry, Expanded) and entry.note == expected
