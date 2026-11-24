"""POST /entries/expand: expands one short entry for the signed-in user (REQ-276).
POST /entries/expand-all: expands every entry of one text box (REQ-277, rules in app.entries.batch); plain-words lines
  are read with AI help (REQ-438, app.entries.ai_read and app.entries.ai_client).
POST /entries/save: saves the reviewed entries as the user's expense records (REQ-278, rules in app.entries.save).
GET /summary: the user's monthly summary by category (REQ-279, rules in app.entries.summary).
GET /entries, PUT /entries/{id}: the saved-entries list and editing one entry (REQ-280, rules in app.entries.edit).
DELETE /entries/{id}: deletes one of the user's entries for good (REQ-281, app.entries.edit).

A rule error is a normal answer (200, ok=false, the exact message), not an HTTP error: the user typed
something the rules reject. An empty text is a bad request (422): the rules do not define an empty entry.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import AuthClaims
from app.auth.middleware import require_auth
from app.db.session import get_session
from app.entries.ai_client import get_ai_reader
from app.entries.ai_read import AiReader
from app.entries.batch import MAX_ENTRIES, EntryResult, TooMany, expand_all, split_entries
from app.entries.clock import today_ist
from app.entries.codes import load_codes
from app.entries.edit import Refused as EditRefused
from app.entries.edit import delete_entry, edit_entry, edit_text, list_month
from app.entries.expand import CodeInfo, EntryError, Expanded, expand, format_paise
from app.entries.save import Refused, Reviewed, UnknownUser, save_reviewed
from app.entries.summary import is_future, month_of, monthly_summary, parse_month
from app.models import Expenses

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
    ai: bool | None = Field(
        default=None, description="true for a plain-words line read with AI help (shown marked AI); absent means false."
    )


class ExpandAllResponse(BaseModel):
    ok: bool = Field(description="false when the whole text box is rejected (error says why, results is empty).")
    error: str | None = None
    results: list[ExpandResult] = Field(default_factory=list, description="One result per entry, in typed order.")


@router.post("/entries/expand-all", response_model=ExpandAllResponse)
async def expand_all_entries(
    body: ExpandAllRequest,
    _auth: Annotated[AuthClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
    reader: Annotated[AiReader, Depends(get_ai_reader)],
) -> ExpandAllResponse:
    outcome = await expand_all(body.text, today_ist(), await load_codes(session), reader)
    if isinstance(outcome, TooMany):
        return ExpandAllResponse(ok=False, error=outcome.message)
    return ExpandAllResponse(ok=True, results=[_result(item) for item in outcome])


def _result(item: EntryResult) -> ExpandResult:
    if isinstance(item.result, EntryError):
        return ExpandResult(typed=item.typed, ok=False, error=item.result.message, ai=item.ai)
    return ExpandResult(typed=item.typed, ok=True, entry=_entry(item.result), ai=item.ai)


def _reviewed(item: ExpandResult) -> Reviewed:
    entry = item.entry
    if entry is None:
        return Reviewed(typed=item.typed, ok=item.ok, error=item.error, ai=bool(item.ai))
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
        ai=bool(item.ai),
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


class CategoryTotalModel(BaseModel):
    code: str = Field(description="Category code, e.g. F")
    category: str = Field(description="Category name, e.g. Food")
    total: str = Field(description="Rupees with 2 decimals, e.g. 590.00")
    total_paise: int


class SummaryResponse(BaseModel):
    month: str = Field(description="The month shown, YYYY-MM.")
    current_month: str = Field(description="The current month in IST, YYYY-MM: the latest month that can be opened.")
    categories: list[CategoryTotalModel] = Field(
        description="One total per category with entries, in the fixed category order; empty when the month has none."
    )
    grand_total: str
    grand_total_paise: int


@router.get("/summary", response_model=SummaryResponse)
async def summary(
    response: Response,
    auth: Annotated[AuthClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
    month: Annotated[str | None, Query(description="YYYY-MM; the current IST month when left out.")] = None,
) -> SummaryResponse:
    # Totals must equal the saved entries when the summary is opened: never served from the response cache.
    response.headers["Cache-Control"] = "no-store"
    today = today_ist()
    bounds = _month_bounds(month, today)
    names = {info.category_code: info.category for info in (await load_codes(session)).values()}
    result = await monthly_summary(session, auth.user_id, bounds[0], bounds[1], names)
    return SummaryResponse(
        month=month_of(bounds[0]),
        current_month=month_of(today),
        categories=[
            CategoryTotalModel(
                code=c.code, category=c.category, total=format_paise(c.total_paise), total_paise=c.total_paise
            )
            for c in result.categories
        ],
        grand_total=format_paise(result.grand_total_paise),
        grand_total_paise=result.grand_total_paise,
    )


def _month_bounds(month: str | None, today: date) -> tuple[date, date]:
    """The month asked for (default: the current IST month); 422 when it is not YYYY-MM or lies in the future."""
    bounds = parse_month(month if month is not None else month_of(today))
    if bounds is None or is_future(bounds[0], today):
        raise HTTPException(status_code=422, detail="validation-error")
    return bounds


class SavedEntry(BaseModel):
    id: str
    typed: str = Field(description="The entry as typed, e.g. `SWG 340 yd` or a plain-words sentence.")
    edit_text: str = Field(
        description="The pre-fill of an edit: `typed`, or for a plain-words entry its short code form, "
        "e.g. `ZMT 450 11/11 dinner`."
    )
    code: str
    merchant: str | None
    category: str
    amount: str = Field(description="Rupees with 2 decimals, e.g. 340.00")
    amount_paise: int
    date: date
    note: str | None


class SavedEntriesResponse(BaseModel):
    month: str = Field(description="The month shown, YYYY-MM.")
    current_month: str = Field(description="The current month in IST, YYYY-MM: the latest month that can be opened.")
    entries: list[SavedEntry] = Field(description="The user's entries of the month, newest date first.")


def _saved(row: Expenses, codes: dict[str, CodeInfo]) -> SavedEntry:
    code = row.merchant_code or row.category_code
    info = codes[code]
    return SavedEntry(
        id=row.id,
        typed=row.typed_text,
        edit_text=edit_text(row),
        code=code,
        merchant=info.merchant,
        category=info.category,
        amount=format_paise(row.amount_paise),
        amount_paise=row.amount_paise,
        date=date.fromisoformat(row.spent_on),
        note=row.note,
    )


@router.get("/entries", response_model=SavedEntriesResponse)
async def saved_entries(
    response: Response,
    auth: Annotated[AuthClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
    month: Annotated[str | None, Query(description="YYYY-MM; the current IST month when left out.")] = None,
) -> SavedEntriesResponse:
    response.headers["Cache-Control"] = "no-store"  # an edit must show at once, never a cached list
    today = today_ist()
    bounds = _month_bounds(month, today)
    codes = await load_codes(session)
    rows = await list_month(session, auth.user_id, bounds[0], bounds[1])
    return SavedEntriesResponse(
        month=month_of(bounds[0]), current_month=month_of(today), entries=[_saved(row, codes) for row in rows]
    )


class EditRequest(ExpandRequest):
    """One short entry replacing the saved one, e.g. `UBR 220 12/11 airport`."""


class EditResponse(BaseModel):
    ok: bool = Field(description="false when the edit was refused (error says why); the entry is then unchanged.")
    error: str | None = None
    entry: SavedEntry | None = None


@router.put("/entries/{expense_id}", response_model=EditResponse)
async def edit_saved_entry(
    expense_id: str,
    body: EditRequest,
    auth: Annotated[AuthClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EditResponse:
    codes = await load_codes(session)
    outcome = await edit_entry(session, auth.user_id, expense_id, body.text, today_ist(), codes)
    if outcome is None:  # unknown, or another user's: never says which
        raise HTTPException(status_code=404, detail="not-found")
    if isinstance(outcome, EditRefused):
        return EditResponse(ok=False, error=outcome.message)
    return EditResponse(ok=True, entry=_saved(outcome, codes))


@router.delete("/entries/{expense_id}", status_code=204, response_class=Response)
async def delete_saved_entry(
    expense_id: str,
    auth: Annotated[AuthClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    if not await delete_entry(session, auth.user_id, expense_id):  # unknown, or another user's: never says which
        raise HTTPException(status_code=404, detail="not-found")
    return Response(status_code=204)


def mount(app: FastAPI) -> None:
    """Registered in the routes glue."""
    app.include_router(router)
