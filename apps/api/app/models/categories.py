# knm-generated: db-design table=categories hash=d6314272418af0e3; generated from the DB design, edit the design and regenerate
from typing import Optional
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Categories(Base):
    __tablename__ = "categories"

    code: Mapped[str] = mapped_column(Text, primary_key=True)  # not mapped: length 1, upper case
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
