"""Plain-words entries read with AI help (REQ-438, WI-066): which lines go to AI, what the AI must answer, and the
rule check every AI answer passes before the user sees it.

Pure: no I/O and no clock. The call to the Claude API lives in app.entries.ai_client.

Rules (docs/workitems/WI-066/impl.md, product owner 23 Nov 2026):
- A line is in code form when its first word is 1 to 3 letters, whatever follows. Code-form lines are expanded by the
  abbreviation rules exactly as before (an unknown code stays `Unknown code "X".`); codes are never guessed.
- Every other line goes to AI, at most MAX_PLAIN per text box; further plain-words lines get TOO_MANY_PLAIN.
- The AI answer follows the rules of a typed entry: a merchant or category from the tables (a merchant sets its
  category; any other merchant is an error), an amount greater than 0 with at most 2 decimals, and a date from
  1 January of the current year up to today.
"""

import re
from datetime import date
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, Field

from app.entries.expand import (
    DATE_FUTURE,
    DATE_INVALID,
    CodeInfo,
    EntryError,
    Expanded,
    _parse_amount,
)

MAX_PLAIN = 5
TOO_MANY_PLAIN = f"Too many plain-words lines (max {MAX_PLAIN})."
AI_UNAVAILABLE = "AI help is not available right now. Type the entry in code form or try again."
AI_UNREADABLE = "The AI could not read this line. Type it in code form."

_CODE_FORM = re.compile(r"[A-Za-z]{1,3}(?:\s|$)")
_NOTE_BREAKS = re.compile(r"\s*[;\r\n][;\r\n\s]*")


def is_code_form(entry: str) -> bool:
    """`SWG 340 yd`, `X 100`, `F`, `F abc` are code form; `paid 450 to zomato`, `Uber 180`, `450 zomato` are not."""
    return _CODE_FORM.match(entry.strip()) is not None


class AiAnswer(BaseModel):
    """What the AI returns for one plain-words line (structured output)."""

    readable: bool = Field(description="false when the line is not an expense or the amount cannot be found")
    merchant_code: str | None = Field(description="the merchant's code from the merchant table, or null")
    other_merchant: str | None = Field(
        description="the merchant named in the line when it is NOT in the merchant table, otherwise null"
    )
    category_code: str | None = Field(description="the category code from the category table, or null")
    amount: str = Field(description="the amount in rupees as written, e.g. 450 or 799.50; empty when none")
    date: str = Field(description="the date of the expense as YYYY-MM-DD, counted from the given today")
    note: str | None = Field(description="what the money was for, in a few words, or null")


class AiFailure(Enum):
    UNAVAILABLE = "unavailable"  # the AI could not be reached (no key, network, rate limit, server error)
    UNREADABLE = "unreadable"  # the AI answered with something that is not a valid entry, or declined


class AiReader(Protocol):
    async def read(self, line: str, today: date, codes: dict[str, CodeInfo]) -> AiAnswer | AiFailure: ...


def failure_message(failure: AiFailure) -> str:
    return AI_UNAVAILABLE if failure is AiFailure.UNAVAILABLE else AI_UNREADABLE


def check_answer(answer: AiAnswer, today: date, codes: dict[str, CodeInfo]) -> Expanded | EntryError:
    """The AI answer as an entry, or the error for that line. Checks run in the order of the REQ-276 error table."""
    if not answer.readable or answer.other_merchant:
        return EntryError(AI_UNREADABLE)
    if answer.merchant_code:
        code = answer.merchant_code.strip().upper()
        info = codes.get(code)
        if info is None or info.merchant is None:
            return EntryError(AI_UNREADABLE)
    elif answer.category_code:
        code = answer.category_code.strip().upper()
        info = codes.get(code)
        if info is None or info.merchant is not None:
            return EntryError(AI_UNREADABLE)
    else:
        return EntryError(AI_UNREADABLE)

    amount = _parse_amount(answer.amount.strip())
    if isinstance(amount, EntryError):
        return amount

    try:
        spent_on = date.fromisoformat(answer.date.strip())
    except ValueError:
        return EntryError(DATE_INVALID)
    if spent_on > today:
        return EntryError(DATE_FUTURE)
    if spent_on < date(today.year, 1, 1):
        return EntryError(DATE_INVALID)

    # A note never holds an entry separator, so the short code form of an edit stays one entry.
    note = _NOTE_BREAKS.sub(" ", answer.note or "").strip() or None
    return Expanded(
        code=code,
        merchant=info.merchant,
        category=info.category,
        category_code=info.category_code,
        amount_paise=amount,
        date=spent_on,
        note=note,
    )
