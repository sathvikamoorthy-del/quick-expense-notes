"""Saves the reviewed entries of one text box as the user's expense records (REQ-278, WI-048).

Rules (docs/workitems/WI-048/impl.md, product owner 22 Nov 2026):
- The text is expanded again at save time (the server is the only source of truth) and must give exactly what the
  user reviewed: same entries, order, typed text, errors and values. Otherwise nothing is saved (REVIEW_CHANGED);
  e.g. a review made before midnight IST whose `td` / `yd` dates have shifted by the time of saving.
- Valid entries are saved, in one transaction; entries with an error are not saved and are returned as failed.
- There is no duplicate check: saving the same text twice creates new records.
- Plain-words lines (REQ-438 q4, WI-066) are saved exactly as the review showed, without asking the AI again. Their
  reviewed values must still pass the rules (app.entries.ai_read.check_answer) against today and the code table, and
  the line must be a plain-words line at the same place; otherwise nothing is saved (REVIEW_CHANGED).
"""

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.entries.ai_read import AiAnswer, check_answer
from app.entries.batch import AiLine, EntryResult, TooMany, plan_all
from app.entries.expand import CodeInfo, EntryError, Expanded, format_paise
from app.models import Expenses, Users

REVIEW_CHANGED = "The entries changed since the review. Press Expand to review them again."


class UnknownUser(Exception):
    """The signed-in user id has no users row (only possible with a hand-made token)."""


@dataclass(frozen=True)
class Reviewed:
    """One entry of the review the user saw, as the web app sends it back. Entry values are None for an error."""

    typed: str
    ok: bool
    error: str | None = None
    code: str | None = None
    merchant: str | None = None
    category: str | None = None
    amount_paise: int | None = None
    date: date | None = None
    note: str | None = None
    ai: bool = False


@dataclass(frozen=True)
class Refused:
    message: str


@dataclass(frozen=True)
class Saved:
    ids: list[str]
    failed: list[EntryResult]


def as_reviewed(item: EntryResult) -> Reviewed:
    """What the review showed for a freshly expanded entry."""
    result = item.result
    if isinstance(result, EntryError):
        return Reviewed(typed=item.typed, ok=False, error=result.message, ai=item.ai)
    return Reviewed(
        typed=item.typed,
        ok=True,
        code=result.code,
        merchant=result.merchant,
        category=result.category,
        amount_paise=result.amount_paise,
        date=result.date,
        note=result.note,
        ai=item.ai,
    )


def _from_review(line: AiLine, seen: Reviewed, today: date, codes: dict[str, CodeInfo]) -> EntryResult | None:
    """The plain-words line as the review showed it, checked again by the rules; None when it does not hold."""
    if seen.typed != line.typed or not seen.ai:
        return None
    if not seen.ok:  # an AI failure or a rule error the user saw: not saved, returned as failed
        return EntryResult(typed=line.typed, result=EntryError(seen.error or ""), ai=True)
    if seen.code is None or seen.amount_paise is None or seen.amount_paise <= 0 or seen.date is None:
        return None
    is_merchant = seen.merchant is not None
    answer = AiAnswer(
        readable=True,
        merchant_code=seen.code if is_merchant else None,
        other_merchant=None,
        category_code=None if is_merchant else seen.code,
        amount=format_paise(seen.amount_paise),
        date=seen.date.isoformat(),
        note=seen.note,
    )
    result = check_answer(answer, today, codes)
    if isinstance(result, EntryError):
        return None
    item = EntryResult(typed=line.typed, result=result, ai=True)
    return item if as_reviewed(item) == seen else None


def match_review(
    reviewed: list[Reviewed], planned: list[EntryResult | AiLine], today: date, codes: dict[str, CodeInfo]
) -> list[EntryResult] | None:
    """The entries to save, when the review still holds for every entry; None when anything changed."""
    if len(reviewed) != len(planned):
        return None
    matched: list[EntryResult] = []
    for seen, item in zip(reviewed, planned, strict=True):
        if isinstance(item, AiLine):
            checked = _from_review(item, seen, today, codes)
            if checked is None:
                return None
            matched.append(checked)
        elif as_reviewed(item) == seen:
            matched.append(item)
        else:
            return None
    return matched


async def save_reviewed(
    session: AsyncSession,
    user_id: str,
    text: str,
    reviewed: list[Reviewed],
    today: date,
    codes: dict[str, CodeInfo],
) -> Saved | Refused:
    """Adds one Expenses row per valid entry to the session; the caller's transaction commits them together."""
    planned = plan_all(text, today, codes)
    if isinstance(planned, TooMany):
        return Refused(planned.message)
    fresh = match_review(reviewed, planned, today, codes)
    if fresh is None:
        return Refused(REVIEW_CHANGED)
    if await session.get(Users, user_id) is None:
        raise UnknownUser(user_id)

    ids: list[str] = []
    failed: list[EntryResult] = []
    for item in fresh:
        if not isinstance(item.result, Expanded):
            failed.append(item)
            continue
        entry = item.result
        expense_id = str(uuid.uuid4())
        session.add(
            Expenses(
                id=expense_id,
                user_id=user_id,
                typed_text=item.typed,
                category_code=entry.category_code,
                merchant_code=entry.code if entry.merchant is not None else None,
                amount_paise=entry.amount_paise,
                spent_on=entry.date.isoformat(),
                note=entry.note,
            )
        )
        ids.append(expense_id)
    await session.flush()
    return Saved(ids=ids, failed=failed)
