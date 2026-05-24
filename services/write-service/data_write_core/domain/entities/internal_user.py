from ..events import EventCollector
from ._entity_root import EntityRoot


class InternalUserEntity(EntityRoot):
    def __init__(
        self,
        user_id: str,
        email: str,
        first_name: str,
        last_name: str,
        collector: EventCollector | None = None,
    ):
        super().__init__(unique_id=user_id, collector=collector or EventCollector())

        self._email = email
        self._first_name = first_name
        self._last_name = last_name
