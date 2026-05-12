from finances.domain.value_objects import Currency
from finances.infrastructure.orm import CurrencyModel


class CurrencyMapper:
    @staticmethod
    def to_domain(model: CurrencyModel) -> Currency:
        return Currency(
            code = model.code,
            name = model.name,
            numeric = model.numeric,
            digits = model.digits
        )
