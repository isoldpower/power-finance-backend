from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import ModelBase


class UserModel(ModelBase):
    """The external id of a user this service has seen synced.

    Kept because every event this service publishes is keyed by the user's
    external (Clerk) id, and nothing else here carries it: the transaction
    events arrive with the internal id alone. Projected from `UserSynced` in
    the same transaction that seeds the user's accounts, so a dispatch that can
    resolve a chart of accounts can always key the events it produces.
    """

    __tablename__ = "ai_users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    external_id: Mapped[str] = mapped_column(String(255), unique=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
