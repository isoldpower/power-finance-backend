from collections.abc import Iterable
from datetime import datetime

from kafka_client_py import headers as Headers


def retry_due_at(message_headers: Iterable[tuple[str, bytes]] | None) -> datetime | None:
    return Headers.get_datetime(
        message_headers,
        Headers.HEADER_RETRY_AT,
    )


class DeferredPartitions:
    def __init__(self) -> None:
        self._until: dict[object, datetime] = {}

    def hold(self, partition: object, until: datetime) -> None:
        self._until[partition] = until

    def due(self, now: datetime) -> list[object]:
        return [partition for partition, until in self._until.items() if until <= now]

    def release(self, partition: object) -> None:
        self._until.pop(partition, None)

    def held(self) -> list[object]:
        return list(self._until)

    def __len__(self) -> int:
        return len(self._until)

    def __contains__(self, partition: object) -> bool:
        return partition in self._until
