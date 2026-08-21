from decimal import ROUND_HALF_UP, Decimal

from data_read_core.shared.exchange_rates import ExchangeRateService, get_rate_service
from data_read_core.shared.money import CURRENCY_CATALOG, CurrencyCatalog, parse_amount

from .dtos import ConversionDTO, ConvertCurrencyQuery
from .logger_shortcuts import log_conversion_served

AMOUNT_FIELD = "amount"


class ConvertCurrencyQueryHandler:
    """The rounding happens here, once. Clients render `to` rather than
    multiplying `rate` themselves, so two clients cannot disagree about the
    last digit."""

    def __init__(
        self,
        rate_service: ExchangeRateService | None = None,
        catalog: CurrencyCatalog | None = None,
    ) -> None:
        self._rate_service = rate_service or get_rate_service()
        self._catalog = catalog or CURRENCY_CATALOG

    async def handle(self, query: ConvertCurrencyQuery) -> ConversionDTO:
        source = await self._catalog.require(query.from_code)
        target = await self._catalog.require(query.to_code)

        amount = parse_amount(query.raw_amount, source.digits, AMOUNT_FIELD)
        rate, fetched_at = await self._rate_service.rate_between(source.code, target.code)
        converted = self._at_scale(amount * rate, target.digits)

        log_conversion_served(source.code, target.code)

        return ConversionDTO(
            from_code=source.code,
            from_amount=amount,
            from_decimals=source.digits,
            to_code=target.code,
            to_amount=converted,
            to_decimals=target.digits,
            rate=rate,
            fetched_at=fetched_at,
        )

    def _at_scale(self, amount: Decimal, decimals: int) -> Decimal:
        return amount.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
