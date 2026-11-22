"""POST /entries/expand: expands one short entry for the signed-in user (REQ-276).
POST /entries/expand-all: expands every entry of one text box (REQ-277, rules in app.entries.batch).
POST /entries/save: saves the reviewed entries as the user's expense records (REQ-278, rules in app.entries.save).

A rule error is a normal answer (200, ok=false, the exact message), not an HTTP error: the user typed
something the rules reject. An empty text is a bad request (422): the rules do not define an empty entry.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import AuthClaims
from app.auth.middleware import require_auth
from app.db.session import get_session
from app.entries.batch import MAX_ENTRIES, EntryResult, TooMany, expand_all, split_entries
from app.entries.clock import today_ist
from app.entries.codes import load_codes
from app.entries.expand import EntryError, Expanded, expand
from app.entries.save import Refused, Reviewed, UnknownUser, save_reviewed

router = APIRouter(tags=["entries"])


class ExpandRequest(BaseModel):
    text: str = Field(max_length=500, description="One short entry, e.g. `SWG 340 yd`.")

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be empty")
        return value


class ExpandedEntry(BaseModel):
    code: str
    merchant: str | None
    category: str
    amount: str = Field(description="Rupees with 2 decimals, e.g. 340.00")
    amount_paise: int
    date: date
    note: str | None


class ExpandResponse(BaseModel):
    ok: bool
    entry: ExpandedEntry | None = None
    error: str | None = None


@router.post("/entries/expand", response_model=ExpandResponse)
async def expand_entry(
    body: ExpandRequest,
    _auth: Annotated[AuthClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ExpandResponse:
    result = expand(body.text, today_ist(), await load_codes(session))
    if isinstance(result, EntryError):
        return ExpandResponse(ok=False, error=result.message)
    return ExpandResponse(ok=True, entry=_entry(result))


def _entry(result: Expanded) -> ExpandedEntry:
    return ExpandedEntry(
        code=result.code,
        merchant=result.merchant,
        category=result.category,
        amount=result.amount,
        amount_paise=result.amount_paise,
        date=result.date,
        note=result.note,
    )


# A technical guard against huge pastes, not a product rule: MAX_ENTRIES entries of 500 characters plus separators.
MAX_TEXT_BOX = MAX_ENTRIES * 500 + 500


class ExpandAllRequest(BaseModel):
    text: str = Field(
        max_length=MAX_TEXT_BOX, description="Several short entries separated by new lines or semicolons."
    )

    @field_validator("text")
    @classmethod
    def has_an_entry(cls, value: str) -> str:
        if not split_entries(value):
            raise ValueError("text must contain at least one entry")
        return value


class ExpandResult(BaseModel):
    typed: str = Field(description="The entry as typed, trimmed.")
    ok: bool
    entry: ExpandedEntry | None = None
    error: str | None = None


class ExpandAllResponse(BaseModel):
    ok: bool = Field(description="false when the whole text box is rejected (error says why, results is empty).")
    error: str | None = None
    results: list[ExpandResult] = Field(default_factory=list, description="One result per entry, in typed order.")


@router.post("/entries/expand-all", response_model=ExpandAllResponse)
async def expand_all_entries(
    body: ExpandAllRequest,
    _auth: Annotated[AuthClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ExpandAllResponse:
    outcome = expand_all(body.text, today_ist(), await load_codes(session))
    if isinstance(outcome, TooMany):
        return ExpandAllResponse(ok=False, error=outcome.message)
    return ExpandAllResponse(ok=True, results=[_result(item) for item in outcome])


def _result(item: EntryResult) -> ExpandResult:
    if isinstance(item.result, EntryError):
        return ExpandResult(typed=item.typed, ok=False, error=item.result.message)
    return ExpandResult(typed=item.typed, ok=True, entry=_entry(item.result))


def _reviewed(item: ExpandResult) -> Reviewed:
    entry = item.entry
    if entry is None:
        return Reviewed(typed=item.typed, ok=item.ok, error=item.error)
    return Reviewed(
        typed=item.typed,
        ok=item.ok,
        error=item.error,
        code=entry.code,
        merchant=entry.merchant,
        category=entry.category,
        amount_paise=entry.amount_paise,
        date=entry.date,
        note=entry.note,
    )


class SaveRequest(ExpandAllRequest):
    reviewed: list[ExpandResult] = Field(
        max_length=MAX_ENTRIES, description="The results of /entries/expand-all that the user reviewed, unchanged."
    )


class SaveResponse(BaseModel):
    ok: bool = Field(description="false when nothing was saved (error says why).")
    error: str | None = None
    saved: int = Field(default=0, description="How many entries were saved as expense records.")
    ids: list[str] = Field(default_factory=list, description="The ids of the saved expense records.")
    failed: list[ExpandResult] = Field(default_factory=list, description="The entries not saved, with their errors.")


@router.post("/entries/save", response_model=SaveResponse)
async def save_entries(
    body: SaveRequest,
    auth: Annotated[AuthClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SaveResponse:
    reviewed = [_reviewed(item) for item in body.reviewed]
    try:
        outcome = await save_reviewed(
            session, auth.user_id, body.text, reviewed, today_ist(), await load_codes(session)
        )
    except UnknownUser:
        raise HTTPException(status_code=401, detail="unauthorized") from None
    if isinstance(outcome, Refused):
        return SaveResponse(ok=False, error=outcome.message)
    return SaveResponse(
        ok=True, saved=len(outcome.ids), ids=outcome.ids, failed=[_result(item) for item in outcome.failed]
    )


def mount(app: FastAPI) -> None:
    """Registered in the routes glue."""
    app.include_router(router)
