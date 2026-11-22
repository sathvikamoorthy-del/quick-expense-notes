# expenses (REQ-278, WI-048); columns as in docs/project/db_design.md and migrations/0004_expenses.sql
from typing import Optional
from sqlalchemy import ForeignKey, ForeignKeyConstraint, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

NOW_ISO_UTC = text("(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))")


class Expenses(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        # a merchant always comes with its own category (uq_merchants_code_category_code)
        ForeignKeyConstraint(
            ["merchant_code", "category_code"], ["merchants.code", "merchants.category_code"], ondelete="RESTRICT"
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # UUID, length 36
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    typed_text: Mapped[str] = mapped_column(Text, nullable=False)  # the short entry as typed, trimmed
    category_code: Mapped[str] = mapped_column(Text, ForeignKey("categories.code", ondelete="RESTRICT"), nullable=False)
    merchant_code: Mapped[Optional[str]] = mapped_column(Text, ForeignKey("merchants.code", ondelete="RESTRICT"))
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)  # > 0
    spent_on: Mapped[str] = mapped_column(Text, nullable=False)  # YYYY-MM-DD
    note: Mapped[Optional[str]] = mapped_column(Text)
    # set by the database (ISO UTC), as in the migration; the app never sends them on insert
    created_at: Mapped[str] = mapped_column(Text, nullable=False, server_default=NOW_ISO_UTC)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, server_default=NOW_ISO_UTC)
