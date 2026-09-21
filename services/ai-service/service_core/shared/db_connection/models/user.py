from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import ModelBase


class UserModel(ModelBase):
    __tablename__ = "ai_users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    external_id: Mapped[str] = mapped_column(String(255), unique=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
