from abc import ABC, abstractmethod

from finances.domain.value_objects import Currency


class CurrencyRepository(ABC):
    @abstractmethod
    def currency_exists(self, currency: Currency) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def currency_code_exists(self, currency_code: str) -> bool:
        raise NotImplementedError()
