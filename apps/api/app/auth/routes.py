"""POST /auth/sign-in (REQ-275): email and password in, a 60-minute token out.

Email and password are plain strings on purpose: an empty one is a failed sign-in (401, the same message as a wrong
password), not a validation error (422). The rules live in app.auth.service.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import INVALID_CREDENTIALS, InvalidCredentials, sign_in
from app.db.session import get_session

router = APIRouter(tags=["auth"])


class SignInRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)


class SignedInUser(BaseModel):
    id: str
    email: str
    display_name: str


class SignInResponse(BaseModel):
    token: str
    expires_in: int = Field(description="Seconds until the token expires (3600).")
    user: SignedInUser


@router.post(
    "/auth/sign-in",
    response_model=SignInResponse,
    responses={401: {"description": "Invalid email or password."}},
)
async def sign_in_route(
    body: SignInRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SignInResponse:
    try:
        result = await sign_in(session, body.email, body.password)
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS) from None
    return SignInResponse(
        token=result.token,
        expires_in=result.expires_in,
        user=SignedInUser(id=result.user_id, email=result.email, display_name=result.display_name),
    )


def mount(app: FastAPI) -> None:
    """Registered in the routes glue."""
    app.include_router(router)
