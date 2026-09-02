from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from ..vocabulary import Severity
from .refusal import EFFECT_PARAMS_INVALID, AutomationRefusal

CURRENCY_CODE_LENGTH = 3


def refuse(path: str, reason: str) -> AutomationRefusal:
    return AutomationRefusal(
        path=path,
        detail_code=EFFECT_PARAMS_INVALID,
        reason=reason,
    )


def require_non_empty_string(params: Mapping[Any, Any], key: str, path: str) -> str:
    match params.get(key):
        case str() as value if value.strip():
            return value
        case _:
            raise refuse(
                f"{path}.{key}",
                f"`{key}` must be a non-empty string.",
            )


def require_severity(params: Mapping[Any, Any], path: str) -> str:
    severity = params.get("severity")
    if severity not in list(Severity):
        raise refuse(f"{path}.severity", f"Legal values: {', '.join(Severity)}.")

    return str(severity)


def require_uuid(params: Mapping[Any, Any], key: str, path: str) -> str:
    try:
        return str(UUID(str(params.get(key))))
    except (ValueError, AttributeError, TypeError) as error:
        raise refuse(f"{path}.{key}", f"`{key}` must be a UUID.") from error


def require_money(money: Any, path: str) -> None:
    match money:
        case {"amount": amount, "currency": currency} if len(money) == 2:
            _require_positive_amount(amount, f"{path}.amount")
            _require_currency_code(currency, f"{path}.currency")
        case _:
            raise refuse(path, "`money` takes exactly `amount` and `currency`.")


def _require_positive_amount(amount: Any, path: str) -> None:
    match amount:
        case str() as raw:
            _require_above_zero(raw, path)
        case _:
            raise refuse(
                path,
                "`amount` must be a decimal string, not a JSON number.",
            )


def _require_above_zero(raw: str, path: str) -> None:
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise refuse(path, "`amount` is not a decimal.") from error

    if parsed <= 0:
        raise refuse(path, "A transfer moves a positive amount.")


def _require_currency_code(currency: Any, path: str) -> None:
    match currency:
        case str() as code if len(code) == CURRENCY_CODE_LENGTH:
            return
        case _:
            raise refuse(
                path,
                "`currency` must be an ISO-4217 alphabetic code.",
            )
