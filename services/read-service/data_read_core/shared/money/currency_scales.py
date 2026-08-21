from data_read_core.shared.http_contract import UnsupportedCurrency
from data_read_core.shared.postgres_orm import CurrencyReadModel

DEFAULT_CURRENCY = "USD"
DEFAULT_DECIMALS = 2


class CurrencyScales:
    """Static reference data, so the table is read once per process and held in
    memory."""

    def __init__(self) -> None:
        self._digits_by_code: dict[str, int] = {}

    async def table(self) -> dict[str, int]:
        if not self._digits_by_code:
            self._digits_by_code = {
                currency.code: currency.digits async for currency in CurrencyReadModel.objects.all()
            }

        return self._digits_by_code

    async def decimals_for(self, currency_code: str) -> int:
        decimals = (await self.table()).get(currency_code.upper())
        if decimals is None:
            raise UnsupportedCurrency(f"Currency {currency_code!r} is not supported")

        return decimals

    async def decimals_or_default(self, currency_code: str | None) -> int:
        if not currency_code:
            return DEFAULT_DECIMALS

        return (await self.table()).get(currency_code.upper(), DEFAULT_DECIMALS)

    async def supported_codes(self) -> list[str]:
        return sorted(await self.table())

    def reset(self) -> None:
        self._digits_by_code = {}


CURRENCY_SCALES = CurrencyScales()
