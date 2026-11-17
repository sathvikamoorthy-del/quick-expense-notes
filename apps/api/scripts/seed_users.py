"""Creates (or updates) the demo account (REQ-275: no self sign-up yet; a seed script creates the accounts).

Usage: python -m scripts.seed_users
The password comes from DEMO_USER_PASSWORD (environment or .env) and is stored only as a bcrypt hash.
The users table must exist first (migrations/0003_users.sql).
"""

import asyncio
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.auth.service import upsert_user
from app.db.session import Database

DEMO_EMAIL = "asha@example.com"
DEMO_NAME = "Asha"


class SeedSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    demo_user_password: str = ""  # DEMO_USER_PASSWORD


async def seed(password: str, url: str | None = None) -> str:
    database = Database.from_url(url)
    try:
        async with database.sessions() as session:
            user = await upsert_user(session, DEMO_EMAIL, password, DEMO_NAME)
            await session.commit()
            return user.id
    finally:
        await database.dispose()


def main() -> int:
    password = SeedSettings().demo_user_password
    if not password:
        print("DEMO_USER_PASSWORD is not set (environment or .env)", file=sys.stderr)
        return 2
    user_id = asyncio.run(seed(password))
    print(f"demo user {DEMO_EMAIL} ready ({user_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
