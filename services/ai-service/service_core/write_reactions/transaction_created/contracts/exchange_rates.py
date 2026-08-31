from decimal import Decimal
from typing import Protocol, runtime_checkable


@runtime_checkable
class ExchangeRates(Protocol):
    async def rate_between(
        self,
        base_code: str,
        quote_code: str,
    ) -> tuple[Decimal, object]: ...
