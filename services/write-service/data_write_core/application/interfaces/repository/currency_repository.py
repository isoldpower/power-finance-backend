from abc import ABC, abstractmethod

from data_write_core.domain.entities import CurrencyEntity


class CurrencyRepository(ABC):
    @abstractmethod
    async def currency_exists(self, currency: CurrencyEntity) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def currency_code_exists(self, currency_code: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def get_decimals_by_code(self) -> dict[str, int]:
        """Fraction digits per currency code — the contract's `decimals`."""

        raise NotImplementedError()
