from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers
from rest_framework.request import Request

from data_read_core.shared.http_contract import DetailCode, ErrorDetail, ValidationFailed
from data_read_core.shared.money import CURRENCY_CATALOG

from .config import (
    DEFAULT_TIMEZONE,
    DEFAULT_WINDOW_LENGTH,
    LIST_SEPARATOR,
    MAXIMUM_WINDOW_LENGTH,
    Granularity,
    IntegerBounds,
    LedgerSide,
    Messages,
    ParamsList,
    ReservedTokens,
)
from .postgres_requests import fetch_open_wallets
from .scope import AnalyticsScope, AnalyticsWindow

DATETIME_FIELD = serializers.DateTimeField()


async def read_analytics_scope(
    request: Request,
    *,
    accepts_categories: bool,
    maximum_window_length: timedelta = MAXIMUM_WINDOW_LENGTH,
) -> AnalyticsScope:
    return AnalyticsScope(
        user_id=request.user.id,
        window=read_window(request, maximum_window_length),
        currency=await read_currency(request),
        timezone=read_timezone(request),
        wallet_identifiers=await read_wallet_identifiers(request),
        categories=read_categories(request) if accepts_categories else None,
    )


def read_window(
    request: Request,
    maximum_window_length: timedelta = MAXIMUM_WINDOW_LENGTH,
) -> AnalyticsWindow:
    until = _read_datetime(request, ParamsList.UNTIL) or datetime.now(UTC)
    since = _read_datetime(request, ParamsList.SINCE) or until - DEFAULT_WINDOW_LENGTH

    if until <= since:
        raise _invalid(
            ParamsList.UNTIL,
            DetailCode.RANGE_INVALID,
            Messages.UNTIL_NOT_AFTER_SINCE,
        )
    if until - since > maximum_window_length:
        raise _invalid(
            ParamsList.SINCE,
            DetailCode.RANGE_TOO_LONG,
            Messages.WINDOW_TOO_LONG.format(days=maximum_window_length.days),
        )

    return AnalyticsWindow(since=since.astimezone(UTC), until=until.astimezone(UTC))


async def read_currency(request: Request) -> str:
    raw_currency = request.query_params.get(ParamsList.CURRENCY)
    if not raw_currency:
        return request.user.preferences.currency

    return (await CURRENCY_CATALOG.require(raw_currency)).code


def read_timezone(request: Request) -> str:
    raw_timezone = (request.query_params.get(ParamsList.TIMEZONE) or "").strip()
    if not raw_timezone:
        return DEFAULT_TIMEZONE

    try:
        ZoneInfo(raw_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise _invalid(
            ParamsList.TIMEZONE,
            DetailCode.INVALID,
            Messages.UNKNOWN_TIMEZONE.format(timezone=raw_timezone),
        ) from None

    return raw_timezone


async def read_wallet_identifiers(request: Request) -> tuple[str, ...] | None:
    requested_identifiers = _read_list(request, ParamsList.WALLET_ID)
    if requested_identifiers is None:
        return None

    open_wallet_identifiers = {
        wallet.identifier for wallet in await fetch_open_wallets(request.user.id)
    }
    normalised_identifiers: list[str] = []
    for requested_identifier in requested_identifiers:
        normalised_identifier = _normalised_uuid(requested_identifier)
        if normalised_identifier not in open_wallet_identifiers:
            raise _invalid(
                ParamsList.WALLET_ID,
                DetailCode.WALLET_UNKNOWN,
                Messages.UNKNOWN_WALLET.format(wallet=requested_identifier),
            )
        if normalised_identifier not in normalised_identifiers:
            normalised_identifiers.append(normalised_identifier)

    return tuple(normalised_identifiers)


def read_categories(request: Request) -> tuple[str | None, ...] | None:
    requested_tokens = _read_list(request, ParamsList.CATEGORY)
    if requested_tokens is None:
        return None

    categories: list[str | None] = []
    for requested_token in requested_tokens:
        category = None if requested_token == ReservedTokens.UNCATEGORISED else requested_token
        if category not in categories:
            categories.append(category)

    return tuple(categories)


def read_side(request: Request, default: LedgerSide = LedgerSide.EXPENSE) -> LedgerSide:
    return read_optional_side(request) or default


def read_optional_side(request: Request) -> LedgerSide | None:
    return read_choice(
        request,
        ParamsList.TYPE,
        LedgerSide,
        DetailCode.TYPE_INVALID,
        Messages.UNKNOWN_SIDE,
    )


def read_granularity(request: Request) -> Granularity | None:
    return read_choice(
        request,
        ParamsList.GRANULARITY,
        Granularity,
        DetailCode.INVALID,
        Messages.UNKNOWN_GRANULARITY,
    )


def read_bounded_integer(
    request: Request,
    bounds: IntegerBounds,
    detail_code: DetailCode,
) -> int:
    raw_value = (request.query_params.get(bounds.parameter) or "").strip()
    if not raw_value:
        return bounds.default

    try:
        parsed_value = int(raw_value)
    except ValueError:
        parsed_value = None

    if parsed_value is None or not bounds.minimum <= parsed_value <= bounds.maximum:
        raise _invalid(
            bounds.parameter,
            detail_code,
            Messages.INTEGER_OUT_OF_RANGE.format(
                parameter=bounds.parameter,
                minimum=bounds.minimum,
                maximum=bounds.maximum,
            ),
        )

    return parsed_value


def read_choice[ChoiceType: StrEnum](
    request: Request,
    parameter: ParamsList,
    choices: type[ChoiceType],
    detail_code: DetailCode,
    message: Messages,
) -> ChoiceType | None:
    raw_choice = (request.query_params.get(parameter) or "").strip().lower()
    if not raw_choice:
        return None

    try:
        return choices(raw_choice)
    except ValueError:
        raise _invalid(
            parameter,
            detail_code,
            message.format(legal=", ".join(choice.value for choice in choices)),
        ) from None


def _read_datetime(request: Request, parameter: ParamsList) -> datetime | None:
    raw_datetime = (request.query_params.get(parameter) or "").strip()
    if not raw_datetime:
        return None

    try:
        return DATETIME_FIELD.to_internal_value(raw_datetime)
    except serializers.ValidationError:
        raise _invalid(
            parameter,
            DetailCode.RANGE_INVALID,
            Messages.UNPARSABLE_DATETIME.format(parameter=parameter),
        ) from None


def _read_list(request: Request, parameter: ParamsList) -> list[str] | None:
    listed_values = [
        listed_value.strip()
        for raw_value in request.query_params.getlist(parameter)
        for listed_value in raw_value.split(LIST_SEPARATOR)
        if listed_value.strip()
    ]

    return listed_values or None


def _normalised_uuid(raw_identifier: str) -> str | None:
    try:
        return str(UUID(raw_identifier))
    except ValueError:
        return None


def _invalid(parameter: str, detail_code: DetailCode, message: str) -> ValidationFailed:
    return ValidationFailed(
        details=[
            ErrorDetail(
                field=str(parameter),
                code=detail_code,
                message=message,
            )
        ]
    )
