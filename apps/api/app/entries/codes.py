"""The code table of the abbreviation rules, read from the categories and merchants tables (DB design).

Reference data changes only with a migration, so the table is loaded once per process and cached.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.entries.expand import CodeInfo
from app.models import Categories, Merchants

_cache: dict[str, CodeInfo] | None = None


async def read_codes(session: AsyncSession) -> dict[str, CodeInfo]:
    """Category codes map to (None, category); merchant codes to (merchant, its category). Keys are upper case."""
    codes: dict[str, CodeInfo] = {}
    for code, name in (await session.execute(select(Categories.code, Categories.name))).all():
        codes[code.upper()] = CodeInfo(merchant=None, category=name)
    merchants = select(Merchants.code, Merchants.name, Categories.name).join(
        Categories, Categories.code == Merchants.category_code
    )
    for code, merchant, category in (await session.execute(merchants)).all():
        codes[code.upper()] = CodeInfo(merchant=merchant, category=category)
    return codes


async def load_codes(session: AsyncSession) -> dict[str, CodeInfo]:
    """The cached code table; read from the database on first use."""
    global _cache
    if _cache is None:
        _cache = await read_codes(session)
    return _cache


def clear_codes_cache() -> None:
    """For tests (and after a reference-data migration in a running process)."""
    global _cache
    _cache = None
