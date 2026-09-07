from typing import Protocol, runtime_checkable

from ..dtos import RateSnapshotDTO


@runtime_checkable
class RateProvider(Protocol):
    name: str

    async def fetch(self, base_code: str) -> RateSnapshotDTO: ...
