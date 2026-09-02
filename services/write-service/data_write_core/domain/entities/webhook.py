import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..events import EventCollector
from ._entity_root import EntityRoot

SECRET_GRACE_PERIOD = timedelta(hours=24)


def generate_webhook_secret() -> str:
    return secrets.token_urlsafe(32)


@dataclass(frozen=True)
class SecretRotation:
    secret: str
    secret_version: int
    previous_secret: str
    previous_secret_version: int
    previous_secret_expires_at: datetime


@dataclass(frozen=True)
class SecretState:
    secret: str
    secret_version: int
    previous_secret: str
    previous_secret_version: int | None
    previous_secret_expires_at: datetime | None


class WebhookEntity(EntityRoot):
    _title: str
    _url: str
    _secret: str
    _secret_version: int
    _previous_secret: str
    _previous_secret_version: int | None
    _previous_secret_expires_at: datetime | None
    _enabled: bool
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
        enabled: bool = True,
        secret_version: int = 1,
        previous_secret: str = "",
        previous_secret_version: int | None = None,
        previous_secret_expires_at: datetime | None = None,
        event_collector: EventCollector | None = None,
    ):
        super().__init__(
            unique_id=id,
            collector=event_collector or EventCollector(),
        )

        self._title = title
        self._url = url
        self._secret = secret
        self._secret_version = secret_version
        self._previous_secret = previous_secret
        self._previous_secret_version = previous_secret_version
        self._previous_secret_expires_at = previous_secret_expires_at
        self._enabled = enabled
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
    def secret_version(self) -> int:
        return self._secret_version

    @property
    def previous_secret(self) -> str:
        return self._previous_secret

    @property
    def previous_secret_version(self) -> int | None:
        return self._previous_secret_version

    @property
    def previous_secret_expires_at(self) -> datetime | None:
        return self._previous_secret_expires_at

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update(
        self,
        now: datetime,
        title: str | None = None,
        url: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        if title is not None:
            self._title = title
        if url is not None:
            self._url = url
        if enabled is not None:
            self._enabled = enabled
        self._updated_at = now

    def secret_snapshot(self) -> SecretState:
        return SecretState(
            secret=self._secret,
            secret_version=self._secret_version,
            previous_secret=self._previous_secret,
            previous_secret_version=self._previous_secret_version,
            previous_secret_expires_at=self._previous_secret_expires_at,
        )

    def rotate_secret(self, now: datetime) -> SecretRotation:
        expires_at = now + SECRET_GRACE_PERIOD
        replaced_secret, replaced_version = self._secret, self._secret_version

        self._previous_secret = replaced_secret
        self._previous_secret_version = replaced_version
        self._previous_secret_expires_at = expires_at

        self._secret = generate_webhook_secret()
        self._secret_version += 1
        self._updated_at = now

        return SecretRotation(
            secret=self._secret,
            secret_version=self._secret_version,
            previous_secret=replaced_secret,
            previous_secret_version=replaced_version,
            previous_secret_expires_at=expires_at,
        )

    def restore_secret(self, state: SecretState, now: datetime) -> None:
        self._secret = state.secret
        self._secret_version = state.secret_version
        self._previous_secret = state.previous_secret
        self._previous_secret_version = state.previous_secret_version
        self._previous_secret_expires_at = state.previous_secret_expires_at
        self._updated_at = now
