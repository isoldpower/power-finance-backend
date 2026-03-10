from django.db.models import Q

from finances.application.interfaces import CurrencyRepository
from finances.domain.value_objects import Currency
from ..orm import CurrencyModel


class DjangoCurrencyRepository(CurrencyRepository):
    def currency_exists(self, currency: Currency) -> bool:
        currency_queryset = CurrencyModel.objects.filter(
            Q(code=currency.code) & Q(digits=currency.digits) & Q(numeric=currency.numeric)
        )

        return currency_queryset.exists()

    def currency_code_exists(self, currency: str) -> bool:
        currency_queryset = CurrencyModel.objects.filter(code=currency)

        return currency_queryset.exists()