from finances.application.interfaces import CurrencyRepository
from finances.domain.value_objects import Currency

from ..orm import CurrencyModel


class DjangoCurrencyRepository(CurrencyRepository):
    async def currency_exists(self, currency: Currency) -> bool:
        currency_queryset = CurrencyModel.objects.filter(
            code=currency.code,
            digits=currency.digits,
            numeric=currency.numeric,
        )

        return await currency_queryset.aexists()

    async def currency_code_exists(self, currency: str) -> bool:
        currency_queryset = CurrencyModel.objects.filter(code=currency)

        return await currency_queryset.aexists()