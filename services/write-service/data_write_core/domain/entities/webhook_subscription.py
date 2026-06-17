from datetime import datetime

from ..events import EventCollector
from ._entity_root import EntityRoot


class WebhookSubscriptionEntity(EntityRoot):
    _webhook_id: str
    _event_type: str
    _is_active: bool
    _created_at: datetime

    def __init__(
        self,
        id: str,
        webhook_id: str,
        event_type: str,
        created_at: datetime,
        is_active: bool = True,
        event_collector: EventCollector | None = None,
    ):
        super().__init__(unique_id=id, collector=event_collector or EventCollector())

        self._webhook_id = webhook_id
        self._event_type = event_type
        self._is_active = is_active
        self._created_at = created_at

    @property
    def webhook_id(self) -> str:
        return self._webhook_id

    @property
    def event_type(self) -> str:
        return self._event_type

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at
