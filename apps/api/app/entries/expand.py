"""Expands one short entry `<code> <amount> [date] [note]` by the abbreviation rules (REQ-276).

Pure: no I/O and no clock. The caller passes today's date (IST, see app.entries.clock) and the code table
(see app.entries.codes), so every rule can be tested with plain values.

Rules (docs/requirements/REQ-276/req.md):
- Leading and trailing spaces are trimmed; one or more spaces separate the fields. The note is the rest of the entry
  after its separating spaces, kept as typed.
- Codes, the date words `td` / `yd` and the `k` suffix are not case-sensitive. Codes are returned in upper case.
- The amount is a positive number with at most 2 decimals, counted as typed (before `k`). `k` means thousand.
- The third field is a date when it is `td`, `yd` or digits/digits; otherwise it is the first word of the note.
  `d/m` takes one or two digits each and means that day in the current year. A future date is not allowed.
- Exactly one error per entry: the checks run in the order of the REQ-276 error table, the first failure wins.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

UNKNOWN_CODE = 'Unknown code "{code}".'
AMOUNT_MISSING = "Amount is missing."
AMOUNT_NOT_POSITIVE = "Amount must be greater than 0."
AMOUNT_DECIMALS = "Amount must have at most 2 decimals."
DATE_INVALID = "Date is not valid."
DATE_FUTURE = "Date cannot be in the future."

_TOKEN = re.compile(r"\S+")
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)")
_DATE_SHAPED = re.compile(r"\d+/\d+")
_DAY_MONTH = re.compile(r"(\d{1,2})/(\d{1,2})")


@dataclass(frozen=True)
class CodeInfo:
    """What a code stands for: the merchant (None for a category code) and the category name."""

    merchant: str | None
    category: str


@dataclass(frozen=True)
class Expanded:
    code: str
    merchant: str | None
    category: str
    amount_paise: int
    date: date
    note: str | None

    @property
    def amount(self) -> str:
        """Rupees with 2 decimals, e.g. "340.00"."""
        return f"{self.amount_paise // 100}.{self.amount_paise % 100:02d}"


@dataclass(frozen=True)
class EntryError:
    message: str


def _next_token(text: str, pos: int) -> tuple[str, int] | None:
    match = _TOKEN.search(text, pos)
    return (match.group(0), match.end()) if match else None


def _parse_amount(token: str) -> int | EntryError:
    """Returns the amount in paise, or the amount error (greater-than-0 is checked before the decimals)."""
    thousand = len(token) > 1 and token[-1] in "kK"
    number = token[:-1] if thousand else token
    if not _NUMBER.fullmatch(number):
        return EntryError(AMOUNT_NOT_POSITIVE)
    value = Decimal(number)
    if value <= 0:
        return EntryError(AMOUNT_NOT_POSITIVE)
    decimals = len(number.split(".", 1)[1]) if "." in number else 0
    if decimals > 2:
        return EntryError(AMOUNT_DECIMALS)
    if thousand:
        value *= 1000
    return int(value * 100)


def _parse_date(token: str, today: date) -> date | EntryError:
    word = token.lower()
    if word == "td":
        return today
    if word == "yd":
        return today - timedelta(days=1)
    match = _DAY_MONTH.fullmatch(token)
    if not match:
        return EntryError(DATE_INVALID)
    try:
        day = date(today.year, int(match.group(2)), int(match.group(1)))
    except ValueError:
        return EntryError(DATE_INVALID)
    return EntryError(DATE_FUTURE) if day > today else day


def _is_date(token: str) -> bool:
    return token.lower() in ("td", "yd") or _DATE_SHAPED.fullmatch(token) is not None


def expand(text: str, today: date, codes: dict[str, CodeInfo]) -> Expanded | EntryError:
    """Expands one entry. `codes` is keyed by upper-case code. Raises ValueError for an entry with no text at all
    (an empty entry is not something the rules define: the caller rejects it before asking)."""
    entry = text.strip()
    first = _next_token(entry, 0)
    if first is None:
        raise ValueError("empty entry")

    typed_code, pos = first
    code = typed_code.upper()
    info = codes.get(code)
    if info is None:
        return EntryError(UNKNOWN_CODE.format(code=typed_code))

    second = _next_token(entry, pos)
    if second is None:
        return EntryError(AMOUNT_MISSING)
    amount_token, pos = second
    amount = _parse_amount(amount_token)
    if isinstance(amount, EntryError):
        return amount

    spent_on = today
    third = _next_token(entry, pos)
    if third is not None and _is_date(third[0]):
        parsed = _parse_date(third[0], today)
        if isinstance(parsed, EntryError):
            return parsed
        spent_on, pos = parsed, third[1]

    note = entry[pos:].lstrip() or None
    return Expanded(
        code=code, merchant=info.merchant, category=info.category, amount_paise=amount, date=spent_on, note=note
    )
