"""Expands several entries typed in one text box (REQ-277, WI-047), plain-words lines with AI help (REQ-438, WI-066).

Rules (docs/workitems/WI-047/impl.md, product owner 22 Nov 2026; docs/workitems/WI-066/impl.md, 23 Nov 2026):
- New lines and semicolons separate entries, also mixed in one text box.
- Each part is trimmed; empty parts (blank lines, `;;`, a trailing `;`, only spaces) are skipped with no result.
- More than MAX_ENTRIES remaining entries reject the whole text box; skipped empty parts do not count.
- Each code-form entry is expanded by the REQ-276 rules in typed order; an error stops only that entry.
- Each other entry is a plain-words line: the first MAX_PLAIN are read with AI help (app.entries.ai_read), the others
  get TOO_MANY_PLAIN. An AI failure stops only that line.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import date

from app.entries.ai_read import (
    MAX_PLAIN,
    TOO_MANY_PLAIN,
    AiFailure,
    AiReader,
    check_answer,
    failure_message,
    is_code_form,
)
from app.entries.expand import CodeInfo, EntryError, Expanded, expand

log = logging.getLogger(__name__)

MAX_ENTRIES = 20
TOO_MANY_ENTRIES = f"Too many entries (max {MAX_ENTRIES})."

_SEPARATOR = re.compile(r"\r\n|[\r\n;]")


@dataclass(frozen=True)
class TooMany:
    message: str = TOO_MANY_ENTRIES


@dataclass(frozen=True)
class EntryResult:
    """One typed entry (trimmed, inner spaces as typed) and what it expanded to; `ai` marks a plain-words line."""

    typed: str
    result: Expanded | EntryError
    ai: bool = False


@dataclass(frozen=True)
class AiLine:
    """A plain-words line still to be read with AI help."""

    typed: str


def split_entries(text: str) -> list[str]:
    """The non-empty, trimmed entries of a text box in typed order."""
    return [part for part in (raw.strip() for raw in _SEPARATOR.split(text)) if part]


def plan_all(text: str, today: date, codes: dict[str, CodeInfo]) -> list[EntryResult | AiLine] | TooMany:
    """Code-form entries expanded by the rules; the first MAX_PLAIN plain-words lines left for AI. Pure."""
    entries = split_entries(text)
    if len(entries) > MAX_ENTRIES:
        return TooMany()
    planned: list[EntryResult | AiLine] = []
    plain = 0
    for entry in entries:
        if is_code_form(entry):
            planned.append(EntryResult(typed=entry, result=expand(entry, today, codes)))
            continue
        plain += 1
        if plain <= MAX_PLAIN:
            planned.append(AiLine(typed=entry))
        else:
            planned.append(EntryResult(typed=entry, result=EntryError(TOO_MANY_PLAIN), ai=True))
    return planned


async def read_line(reader: AiReader, line: str, today: date, codes: dict[str, CodeInfo]) -> Expanded | EntryError:
    """An AI failure, or anything the reader raises, stops only this line with the unavailable message."""
    try:
        answer = await reader.read(line, today, codes)
    except Exception:
        log.exception("AI reader raised; the line is shown as unavailable")
        answer = AiFailure.UNAVAILABLE
    if isinstance(answer, AiFailure):
        return EntryError(failure_message(answer))
    return check_answer(answer, today, codes)


async def expand_all(
    text: str, today: date, codes: dict[str, CodeInfo], reader: AiReader
) -> list[EntryResult] | TooMany:
    """Every entry of the text box in typed order; the plain-words lines are read concurrently."""
    planned = plan_all(text, today, codes)
    if isinstance(planned, TooMany):
        return planned
    lines = [item for item in planned if isinstance(item, AiLine)]
    answers = iter(await asyncio.gather(*(read_line(reader, line.typed, today, codes) for line in lines)))
    return [
        item if isinstance(item, EntryResult) else EntryResult(typed=item.typed, result=next(answers), ai=True)
        for item in planned
    ]
