import secrets
from datetime import datetime

from ..events import EventCollector
from ._entity_root import EntityRoot


def generate_webhook_secret() -> str:
    return secrets.token_urlsafe(32)


class WebhookEntity(EntityRoot):
    _title: str
    _url: str
    _secret: str
    _is_active: bool
    _user_id: str
    _created_at: datetime
    _updated_at: datetime

    def __init__(
        self,
        id: str,
        title: str,
        url: str,
        secret: str,
        user_id: str,
        created_at: datetime,
        updated_at: datetime,
        is_active: bool = True,
        event_collector: EventCollector | None = None,
    ):
        super().__init__(unique_id=id, collector=event_collector or EventCollector())

        self._title = title
        self._url = url
        self._secret = secret
        self._is_active = is_active
        self._user_id = user_id
        self._created_at = created_at
        self._updated_at = updated_at

    @property
    def title(self) -> str:
        return self._title

    @property
    def url(self) -> str:
        return self._url

    @property
    def secret(self) -> str:
        return self._secret

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update(self, now: datetime, title: str | None = None, url: str | None = None) -> None:
        if title is not None:
            self._title = title
        if url is not None:
            self._url = url
        self._updated_at = now

    def rotate_secret(self, now: datetime) -> str:
        self._secret = generate_webhook_secret()
        self._updated_at = now

        return self._secret

    def restore_secret(self, previous_secret: str, now: datetime) -> None:
        """Inverse of rotate_secret. Compensation hook only — used by SAGA
        rollback when an outbox emission fails after the rotation commit."""
        self._secret = previous_secret
        self._updated_at = now
