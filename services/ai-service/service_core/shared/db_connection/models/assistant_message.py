from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import ModelBase


class AssistantMessageModel(ModelBase):
    """One turn of the single rolling conversation a user has with the
    assistant.

    Keyed by the EXTERNAL (Clerk) id rather than the internal one, because the
    socket and the HTTP edge both authenticate on the gateway's `X-User-Id`
    header and neither carries the internal id. It also means a user can hold a
    conversation before `UserSynced` has seeded their chart of accounts.
    """

    __tablename__ = "ai_assistant_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255))

    role: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text, default="")
    # Always a list, never null: a message that cites nothing has `[]`.
    refs: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # The one order the feed is ever read in — newest first, id breaking
        # ties — so a keyset page is an index scan.
        Index(
            "ai_assistant_messages_feed_idx",
            "external_id",
            created_at.desc(),
            id.desc(),
        ),
    )
