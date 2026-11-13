# knm-generated: db-design table=merchants hash=bdb648ada66eb0ed; generated from the DB design, edit the design and regenerate
from typing import Optional
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Merchants(Base):
    __tablename__ = "merchants"

    code: Mapped[str] = mapped_column(Text, primary_key=True)  # not mapped: length 3, upper case
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    category_code: Mapped[str] = mapped_column(Text, ForeignKey("categories.code", ondelete="RESTRICT"), nullable=False, index=True)  # not mapped: UQ (code, category_code) for expenses FK
