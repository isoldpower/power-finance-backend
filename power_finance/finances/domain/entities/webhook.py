import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4, UUID

from .webhook_type import WebhookType


@dataclass
class WebhookCreateData:
    title: str
    url: str
    user_id: int
    subscribed_events: list[WebhookType]


@dataclass
class Webhook:
    id: UUID
    user_id: int
    title: str
    url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    _secret: str = field(repr=False)
    _subscribed_events: list[WebhookType] = field(default_factory=list)

    @classmethod
    def _generate_secret(cls) -> str:
        return secrets.token_urlsafe(32)

    @classmethod
    def create(cls, data: WebhookCreateData) -> Webhook:
        title = data.title.strip()
        url = data.url.strip()
        timestamp = datetime.now()

        if not title:
            raise ValueError("Webhook title cannot be empty")
        if not url:
            raise ValueError("Webhook url cannot be empty")
        if not data.user_id:
            raise ValueError("Webhook user_id cannot be empty")

        created_webhook: Webhook = cls(
            id=uuid4(),
            user_id=data.user_id,
            title=data.title,
            url=data.url,
            is_active=True,
            _subscribed_events=data.subscribed_events,
            _secret=cls._generate_secret(),
            created_at=timestamp,
            updated_at=timestamp,
        )

        return created_webhook

    @classmethod
    def from_persistence(
        cls,
        id: UUID,
        user_id: int,
        title: str,
        url: str,
        is_active: bool,
        secret: str,
        subscribed_events: list[WebhookType],
        created_at: datetime,
        updated_at: datetime,
    ):
        return cls(
            id=id,
            user_id=user_id,
            title=title,
            url=url,
            is_active=is_active,
            _secret=secret,
            _subscribed_events=subscribed_events,
            created_at=created_at,
            updated_at=updated_at,
        )

    def sign_payload(self, payload: str) -> str:
        digest = hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return f"v1={digest}"

    @property
    def secret(self) -> str:
        return self._secret

    @property
    def subscribed_events(self) -> list[WebhookType]:
        return self._subscribed_events

    def disable_webhook(self):
        self.is_active = False

    def enable_webhook(self):
        self.is_active = True

    def rotate_secret(self):
        self._secret = self._generate_secret()

    def subscribe(self, event_type: WebhookType):
        self._subscribed_events.append(event_type)

    def unsubscribe(self, event_type: WebhookType):
        self._subscribed_events = [
            event for event in self._subscribed_events
            if event.value != event_type.value
        ]