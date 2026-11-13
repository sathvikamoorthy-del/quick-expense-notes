"""POST /entries/expand: expands one short entry for the signed-in user (REQ-276).

A rule error is a normal answer (200, ok=false, the exact REQ-276 message), not an HTTP error: the user typed
something the rules reject. An empty text is a bad request (422): the rules do not define an empty entry.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import AuthClaims
from app.auth.middleware import require_auth
from app.db.session import get_session
from app.entries.clock import today_ist
from app.entries.codes import load_codes
from app.entries.expand import EntryError, expand

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
    return ExpandResponse(
        ok=True,
        entry=ExpandedEntry(
            code=result.code,
            merchant=result.merchant,
            category=result.category,
            amount=result.amount,
            amount_paise=result.amount_paise,
            date=result.date,
            note=result.note,
        ),
    )


def mount(app: FastAPI) -> None:
    """Registered in the routes glue."""
    app.include_router(router)
