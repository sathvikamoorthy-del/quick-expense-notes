"""The monthly summary by category (REQ-279, WI-049): computed from the saved expenses each time, never stored.

Rules (docs/workitems/WI-049/impl.md, product owner 22 Nov 2026):
- Only the user's expenses dated in the month count (`spent_on` from the 1st to the last day).
- One total per category that has expenses, in CATEGORY_ORDER, plus a grand total; all sums in integer paise.
- A month is written `YYYY-MM`; a month after the current IST month cannot be opened.
"""

import re
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Expenses

# The sample's order (03-sample-entries.md), then Utilities and Other (product owner, q4)
CATEGORY_ORDER = ("F", "T", "R", "E", "H", "S", "U", "O")

_MONTH = re.compile(r"(\d{4})-(0[1-9]|1[0-2])")


@dataclass(frozen=True)
class CategoryTotal:
    code: str
    category: str
    total_paise: int


@dataclass(frozen=True)
class Summary:
    categories: list[CategoryTotal]

    @property
    def grand_total_paise(self) -> int:
        return sum(c.total_paise for c in self.categories)


def parse_month(text: str) -> tuple[date, date] | None:
    """`YYYY-MM` -> (first day of the month, first day of the next month); None when not a month."""
    match = _MONTH.fullmatch(text)
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if year < 1:
        return None
    start = date(year, month, 1)
    return start, date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)


def month_of(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def is_future(month_start: date, today: date) -> bool:
    return month_start > date(today.year, today.month, 1)


async def monthly_summary(
    session: AsyncSession, user_id: str, month_start: date, next_month_start: date, category_names: dict[str, str]
) -> Summary:
    """`category_names` maps category code to name (from the cached code table). ISO date text sorts as dates, so the
    range on spent_on uses the (user_id, spent_on) index."""
    query = (
        select(Expenses.category_code, func.sum(Expenses.amount_paise))
        .where(
            Expenses.user_id == user_id,
            Expenses.spent_on >= month_start.isoformat(),
            Expenses.spent_on < next_month_start.isoformat(),
        )
        .group_by(Expenses.category_code)
    )
    totals = {code: int(total) for code, total in (await session.execute(query)).all()}
    order = {code: i for i, code in enumerate(CATEGORY_ORDER)}
    return Summary(
        categories=[
            CategoryTotal(code=code, category=category_names.get(code, code), total_paise=totals[code])
            for code in sorted(totals, key=lambda c: (order.get(c, len(order)), c))
        ]
    )
