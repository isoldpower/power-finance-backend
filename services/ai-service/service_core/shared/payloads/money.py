from decimal import Decimal, InvalidOperation

from kafka_client_py import PoisonError


def parse_money(raw: str) -> Decimal:
    try:
        return Decimal(raw or "0")
    except InvalidOperation as error:
        raise PoisonError(f"amount {raw!r} is not a decimal") from error
