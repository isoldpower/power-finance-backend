from ..events import EventCollector
from ._entity_root import EntityRoot


class InternalUserEntity(EntityRoot):
    def __init__(
        self,
        user_id: str,
        external_id: str,
        email: str,
        first_name: str,
        last_name: str,
        collector: EventCollector | None = None,
    ):
        super().__init__(unique_id=user_id, collector=collector or EventCollector())

        self._external_id = external_id
        self._email = email
        self._first_name = first_name
        self._last_name = last_name

    @property
    def external_id(self) -> str:
        return self._external_id
