"""Expands several entries typed in one text box (REQ-277, WI-047).

Pure like app.entries.expand: no I/O and no clock. Rules (docs/workitems/WI-047/impl.md, product owner 22 Nov 2026):
- New lines and semicolons separate entries, also mixed in one text box.
- Each part is trimmed; empty parts (blank lines, `;;`, a trailing `;`, only spaces) are skipped with no result.
- More than MAX_ENTRIES remaining entries reject the whole text box; skipped empty parts do not count.
- Each entry is expanded by the REQ-276 rules in typed order; an error stops only that entry.
"""

import re
from dataclasses import dataclass
from datetime import date

from app.entries.expand import CodeInfo, EntryError, Expanded, expand

MAX_ENTRIES = 20
TOO_MANY_ENTRIES = f"Too many entries (max {MAX_ENTRIES})."

_SEPARATOR = re.compile(r"\r\n|[\r\n;]")


@dataclass(frozen=True)
class TooMany:
    message: str = TOO_MANY_ENTRIES


@dataclass(frozen=True)
class EntryResult:
    """One typed entry (trimmed, inner spaces as typed) and what it expanded to."""

    typed: str
    result: Expanded | EntryError


def split_entries(text: str) -> list[str]:
    """The non-empty, trimmed entries of a text box in typed order."""
    return [part for part in (raw.strip() for raw in _SEPARATOR.split(text)) if part]


def expand_all(text: str, today: date, codes: dict[str, CodeInfo]) -> list[EntryResult] | TooMany:
    entries = split_entries(text)
    if len(entries) > MAX_ENTRIES:
        return TooMany()
    return [EntryResult(typed=entry, result=expand(entry, today, codes)) for entry in entries]
