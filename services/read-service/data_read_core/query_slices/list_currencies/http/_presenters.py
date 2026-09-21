from ..dtos import CurrencyDTO


def present_one(currency: CurrencyDTO) -> dict:
    return {
        "code": currency.code,
        "symbol": currency.symbol,
        "name": currency.name,
        "decimals": currency.decimals,
    }


def present_many(currencies: list[CurrencyDTO]) -> list[dict]:
    return [present_one(currency) for currency in currencies]
