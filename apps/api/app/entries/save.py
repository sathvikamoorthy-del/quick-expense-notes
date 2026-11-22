"""Saves the reviewed entries of one text box as the user's expense records (REQ-278, WI-048).

Rules (docs/workitems/WI-048/impl.md, product owner 22 Nov 2026):
- The text is expanded again at save time (the server is the only source of truth) and must give exactly what the
  user reviewed: same entries, order, typed text, errors and values. Otherwise nothing is saved (REVIEW_CHANGED);
  e.g. a review made before midnight IST whose `td` / `yd` dates have shifted by the time of saving.
- Valid entries are saved, in one transaction; entries with an error are not saved and are returned as failed.
- There is no duplicate check: saving the same text twice creates new records.
"""

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.entries.batch import EntryResult, TooMany, expand_all
from app.entries.expand import CodeInfo, EntryError, Expanded
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
        return Reviewed(typed=item.typed, ok=False, error=result.message)
    return Reviewed(
        typed=item.typed,
        ok=True,
        code=result.code,
        merchant=result.merchant,
        category=result.category,
        amount_paise=result.amount_paise,
        date=result.date,
        note=result.note,
    )


def same_as_reviewed(reviewed: list[Reviewed], fresh: list[EntryResult]) -> bool:
    return reviewed == [as_reviewed(item) for item in fresh]


async def save_reviewed(
    session: AsyncSession,
    user_id: str,
    text: str,
    reviewed: list[Reviewed],
    today: date,
    codes: dict[str, CodeInfo],
) -> Saved | Refused:
    """Adds one Expenses row per valid entry to the session; the caller's transaction commits them together."""
    fresh = expand_all(text, today, codes)
    if isinstance(fresh, TooMany):
        return Refused(fresh.message)
    if not same_as_reviewed(reviewed, fresh):
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
