from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Note
from app.db.session import Database, get_session


@pytest.fixture
async def database(tmp_path):
    db = Database.from_url(f"file:{tmp_path}/test.db")
    await db.create_all()
    yield db
    await db.dispose()


async def test_round_trip_insert_and_select(database):
    async with database.sessions() as session:
        session.add(Note(title="first"))
        await session.commit()
    async with database.sessions() as session:
        notes = (await session.scalars(select(Note))).all()
    assert [n.title for n in notes] == ["first"]
    assert notes[0].created_at is not None


def make_app(database):
    app = FastAPI()
    app.state.db = database
    router = APIRouter()

    @router.post("/notes")
    async def add(title: str, session: Annotated[AsyncSession, Depends(get_session)]):
        session.add(Note(title=title))
        if title == "boom":
            raise RuntimeError("fail after add")
        return {"ok": True}

    @router.get("/notes")
    async def list_notes(session: Annotated[AsyncSession, Depends(get_session)]):
        return [n.title for n in (await session.scalars(select(Note))).all()]

    app.include_router(router)
    return app


def test_the_session_dependency_commits_on_success_and_rolls_back_on_error(database):
    client = TestClient(make_app(database), raise_server_exceptions=False)
    assert client.post("/notes", params={"title": "kept"}).status_code == 200
    assert client.post("/notes", params={"title": "boom"}).status_code == 500
    assert client.get("/notes").json() == ["kept"]
