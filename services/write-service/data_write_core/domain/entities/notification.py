from datetime import datetime

from ..events import EventCollector
from ._entity_root import EntityRoot


class NotificationEntity(EntityRoot):
    _short: str
    _message: str
    _payload: dict | None
    _is_read: bool
    _user_id: str
    _created_at: datetime

    def __init__(
        self,
        id: str,
        short: str,
        message: str,
        user_id: str,
        created_at: datetime,
        payload: dict | None = None,
        is_read: bool = False,
        event_collector: EventCollector | None = None,
    ):
        super().__init__(unique_id=id, collector=event_collector or EventCollector())

        self._short = short
        self._message = message
        self._payload = payload
        self._is_read = is_read
        self._user_id = user_id
        self._created_at = created_at

    @property
    def short(self) -> str:
        return self._short

    @property
    def message(self) -> str:
        return self._message

    @property
    def payload(self) -> dict | None:
        return self._payload

    @property
    def is_read(self) -> bool:
        return self._is_read

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def acknowledge(self) -> None:
        self._is_read = True

    def unacknowledge(self) -> None:
        """Inverse of acknowledge. Compensation hook only — used by SAGA
        rollback when an outbox emission fails after the ack commit."""
        self._is_read = False
