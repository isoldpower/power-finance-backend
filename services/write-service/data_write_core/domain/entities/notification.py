from datetime import datetime

from ..events import EventCollector
from ._entity_root import EntityRoot

DEFAULT_SEVERITY = "info"


class NotificationEntity(EntityRoot):
    _title: str
    _body: str
    _payload: dict | None
    _severity: str
    _subject_type: str | None
    _subject_id: str | None
    _acknowledged_at: datetime | None
    _user_id: str
    _created_at: datetime
    _updated_at: datetime | None

    def __init__(
        self,
        id: str,
        title: str,
        body: str,
        user_id: str,
        created_at: datetime,
        payload: dict | None = None,
        severity: str = DEFAULT_SEVERITY,
        subject_type: str | None = None,
        subject_id: str | None = None,
        acknowledged_at: datetime | None = None,
        updated_at: datetime | None = None,
        event_collector: EventCollector | None = None,
    ):
        super().__init__(unique_id=id, collector=event_collector or EventCollector())

        self._title = title
        self._body = body
        self._payload = payload
        self._severity = severity
        self._subject_type = subject_type
        self._subject_id = subject_id
        self._acknowledged_at = acknowledged_at
        self._user_id = user_id
        self._created_at = created_at
        self._updated_at = updated_at

    @property
    def title(self) -> str:
        return self._title

    @property
    def body(self) -> str:
        return self._body

    @property
    def payload(self) -> dict | None:
        return self._payload

    @property
    def severity(self) -> str:
        return self._severity

    @property
    def subject_type(self) -> str | None:
        return self._subject_type

    @property
    def subject_id(self) -> str | None:
        return self._subject_id

    @property
    def acknowledged_at(self) -> datetime | None:
        return self._acknowledged_at

    @property
    def is_acknowledged(self) -> bool:
        """The fact and its time are one field, so "read" is derived rather than
        stored beside the timestamp where the two could disagree."""

        return self._acknowledged_at is not None

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    def acknowledge(self, at: datetime) -> None:
        """Idempotent: a second acknowledgement keeps the FIRST timestamp.

        `acknowledged_at` records when the user saw it, and re-tapping a bell
        does not move that moment.
        """

        if self.is_acknowledged:
            return

        self._acknowledged_at = at
        self._updated_at = at

    def unacknowledge(self) -> None:
        """Inverse of acknowledge. Compensation hook only — used by SAGA
        rollback when an outbox emission fails after the ack commit."""

        self._acknowledged_at = None
