# users (REQ-275, WI-039); columns as in docs/project/db_design.md and migrations/0003_users.sql
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Users(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # UUID, length 36
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)  # stored lower-case
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)  # bcrypt hash; never the password
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)  # ISO UTC
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)  # ISO UTC
