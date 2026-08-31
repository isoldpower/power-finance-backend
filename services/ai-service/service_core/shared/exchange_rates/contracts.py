from typing import Protocol, runtime_checkable

from .rate_snapshot import RateSnapshot


@runtime_checkable
class RateProvider(Protocol):
    """A feed of exchange rates, whichever one is configured."""

    name: str

    async def fetch(self, base_code: str) -> RateSnapshot: ...
