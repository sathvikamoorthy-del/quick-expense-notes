"""Database handle (engine and session factory) and the FastAPI session dependency."""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.base import Base
from app.db.engine import create_engine


class Database:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine
        self.sessions = async_sessionmaker(engine, expire_on_commit=False)

    @classmethod
    def from_url(cls, url: str | None = None) -> "Database":
        return cls(create_engine(url))

    async def create_all(self) -> None:
        """Creates the tables of Base.metadata. Development and tests only: schema changes are migrations."""
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request: committed when the handler returns, rolled back when it raises."""
    database: Database = request.app.state.db
    async with database.sessions() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
