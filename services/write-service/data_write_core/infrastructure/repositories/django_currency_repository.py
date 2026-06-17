from data_write_core.application.interfaces import CurrencyRepository
from data_write_core.domain.entities import CurrencyEntity

from ..orm import CurrencyModel


class DjangoCurrencyRepository(CurrencyRepository):
    async def currency_exists(self, currency: CurrencyEntity) -> bool:
        return await CurrencyModel.objects.filter(code=currency.unique_id).aexists()

    async def currency_code_exists(self, currency_code: str) -> bool:
        return await CurrencyModel.objects.filter(code=currency_code).aexists()
