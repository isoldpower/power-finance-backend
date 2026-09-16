from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import ModelBase


class AssistantQuotaModel(ModelBase):
    __tablename__ = "ai_assistant_quotas"

    external_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    message_allowance: Mapped[int] = mapped_column(Integer)
    messages_consumed: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
