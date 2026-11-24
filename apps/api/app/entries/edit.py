"""The saved-entries list, editing one saved entry (REQ-280, WI-052) and deleting one (REQ-281, WI-061).

Rules (docs/workitems/WI-052/impl.md, product owner 22 Nov 2026):
- The list shows the user's entries of one month, newest date first (the newest saved first on the same date).
- An edit re-types one short entry. The REQ-276 rules and messages apply; an invalid edit changes nothing.
- No date, `td`, `yd` and `dd/mm` count from the day the entry was saved (the IST date of created_at), so re-saving the
  pre-filled text keeps the date; a date after today is still refused as in the future.
- The edited entry replaces the old one in place: same id, owner and created_at; updated_at is set to now.
- An entry read with AI help (REQ-438 q5, WI-066) keeps its sentence as typed_text, but the edit is pre-filled with
  its short code form (edit_text), e.g. `ZMT 450 11/11 dinner`, and the rules apply. AI-read dates always lie in the
  year the entry was saved (WI-066 q2), so `d/m` counted from the saved day gives the same date back.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.entries.ai_read import is_code_form
from app.entries.batch import split_entries
from app.entries.clock import IST
from app.entries.expand import CodeInfo, EntryError, expand, format_paise
from app.models import Expenses

ONE_ENTRY_ONLY = "Type one entry only."


@dataclass(frozen=True)
class Refused:
    message: str


def saved_day(created_at: str) -> date:
    """The IST date of an ISO UTC timestamp: "2026-11-12T19:00:00.000Z" (00:30 IST on 13 Nov) -> 13 Nov 2026."""
    moment = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(IST).date()


def edit_text(row: Expenses) -> str:
    """The pre-fill of an edit: the entry as typed, or for a plain-words entry its short code form
    `<code> <amount> <d/m> [note]` (whole rupees without decimals): 45000 paise on 11 Nov -> `ZMT 450 11/11 dinner`."""
    if is_code_form(row.typed_text):
        return row.typed_text
    amount = format_paise(row.amount_paise).removesuffix(".00")
    spent_on = date.fromisoformat(row.spent_on)
    parts = [row.merchant_code or row.category_code, amount, f"{spent_on.day}/{spent_on.month}"]
    if row.note:
        parts.append(row.note)
    return " ".join(parts)


async def list_month(session: AsyncSession, user_id: str, month_start: date, next_month_start: date) -> list[Expenses]:
    query = (
        select(Expenses)
        .where(
            Expenses.user_id == user_id,
            Expenses.spent_on >= month_start.isoformat(),
            Expenses.spent_on < next_month_start.isoformat(),
        )
        .order_by(Expenses.spent_on.desc(), Expenses.created_at.desc())
    )
    return list((await session.execute(query)).scalars())


async def edit_entry(
    session: AsyncSession, user_id: str, expense_id: str, text: str, today: date, codes: dict[str, CodeInfo]
) -> Expenses | Refused | None:
    """The updated row, a refusal (nothing changed), or None when the user has no entry with this id."""
    row = (
        await session.execute(select(Expenses).where(Expenses.id == expense_id, Expenses.user_id == user_id))
    ).scalar_one_or_none()
    if row is None:
        return None
    entries = split_entries(text)
    if len(entries) != 1:
        return Refused(ONE_ENTRY_ONLY)
    result = expand(entries[0], today, codes, reference=saved_day(row.created_at))
    if isinstance(result, EntryError):
        return Refused(result.message)
    row.typed_text = entries[0]
    row.category_code = result.category_code
    row.merchant_code = result.code if result.merchant is not None else None
    row.amount_paise = result.amount_paise
    row.spent_on = result.date.isoformat()
    row.note = result.note
    row.updated_at = func.strftime("%Y-%m-%dT%H:%M:%fZ", "now")  # set by SQLite, same format as the default
    await session.flush()
    await session.refresh(row)
    return row


async def delete_entry(session: AsyncSession, user_id: str, expense_id: str) -> bool:
    """Removes the user's entry for good (REQ-281: hard delete, no undo). False when the user has no entry with this id,
    so another user's entry is never touched and never revealed."""
    result = await session.execute(delete(Expenses).where(Expenses.id == expense_id, Expenses.user_id == user_id))
    return bool(getattr(result, "rowcount", 0))
