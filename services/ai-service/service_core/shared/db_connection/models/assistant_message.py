from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import ModelBase


class AssistantMessageModel(ModelBase):
    __tablename__ = "ai_assistant_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255))

    role: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text, default="")
    refs: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index(
            "ai_assistant_messages_feed_idx",
            "external_id",
            created_at.desc(),
            id.desc(),
        ),
    )
