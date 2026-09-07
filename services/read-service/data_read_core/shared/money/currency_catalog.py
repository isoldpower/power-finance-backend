from dataclasses import dataclass

from data_read_core.shared.http_contract import UnsupportedCurrency
from data_read_core.shared.postgres_orm import CurrencyReadModel

DEFAULT_CURRENCY = "USD"
DEFAULT_DECIMALS = 2


@dataclass(frozen=True)
class CurrencyRecord:
    code: str
    name: str
    symbol: str
    digits: int

    @classmethod
    def from_read_model(cls, model: CurrencyReadModel) -> "CurrencyRecord":
        return cls(
            code=model.code,
            name=model.name,
            symbol=model.symbol,
            digits=model.digits,
        )


class CurrencyCatalog:
    def __init__(self) -> None:
        self._records: dict[str, CurrencyRecord] = {}

    async def records(self) -> dict[str, CurrencyRecord]:
        if not self._records:
            self._records = {
                currency.code: CurrencyRecord.from_read_model(currency)
                async for currency in CurrencyReadModel.objects.all()
            }

        return self._records

    async def listing(self) -> list[CurrencyRecord]:
        return [record for _, record in sorted((await self.records()).items())]

    async def require(self, currency_code: str) -> CurrencyRecord:
        record = (await self.records()).get(currency_code.strip().upper())
        if record is None:
            raise UnsupportedCurrency(f"Currency {currency_code!r} is not supported")

        return record

    async def supports(self, currency_code: str) -> bool:
        return currency_code.strip().upper() in await self.records()

    async def decimals_for(self, currency_code: str) -> int:
        return (await self.require(currency_code)).digits

    async def decimals_or_default(self, currency_code: str | None) -> int:
        if not currency_code:
            return DEFAULT_DECIMALS

        record = (await self.records()).get(currency_code.upper())

        return record.digits if record is not None else DEFAULT_DECIMALS

    async def supported_codes(self) -> list[str]:
        return sorted(await self.records())

    def reset(self) -> None:
        self._records = {}


CURRENCY_CATALOG = CurrencyCatalog()
