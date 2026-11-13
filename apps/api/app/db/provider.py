"""Registered in the providers glue (outermost): the app gets one Database as app.state.db, disposed at shutdown."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import Database


def database_provider(app: FastAPI) -> Database:
    database = Database.from_url()
    app.state.db = database
    inner = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        async with inner(application):
            try:
                yield
            finally:
                await database.dispose()

    app.router.lifespan_context = lifespan
    return database
