from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework.request import Request

from data_read_core.shared.http_contract import DetailCode
from data_read_core.shared.money import CURRENCY_CATALOG

from .config import (
    DEFAULT_TIMEZONE,
    DEFAULT_WINDOW_LENGTH,
    MAXIMUM_WINDOW_LENGTH,
    Granularity,
    LedgerSide,
    Messages,
    ParamsList,
    ReservedTokens,
)
from .ledger_rows import AnalyticsCategory
from .postgres_requests import fetch_open_wallets, fetch_requested_categories
from .request_primitives import (
    invalid_parameter,
    normalised_uuid,
    read_choice,
    read_datetime,
    read_list,
)
from .scope import AnalyticsScope, AnalyticsWindow


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
        categories=await read_categories(request) if accepts_categories else None,
    )


def read_window(
    request: Request,
    maximum_window_length: timedelta = MAXIMUM_WINDOW_LENGTH,
) -> AnalyticsWindow:
    until = read_datetime(request, ParamsList.UNTIL) or datetime.now(UTC)
    since = read_datetime(request, ParamsList.SINCE) or until - DEFAULT_WINDOW_LENGTH

    if until <= since:
        raise invalid_parameter(
            ParamsList.UNTIL,
            DetailCode.RANGE_INVALID,
            Messages.UNTIL_NOT_AFTER_SINCE,
        )
    if until - since > maximum_window_length:
        raise invalid_parameter(
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
        raise invalid_parameter(
            ParamsList.TIMEZONE,
            DetailCode.INVALID,
            Messages.UNKNOWN_TIMEZONE.format(timezone=raw_timezone),
        ) from None

    return raw_timezone


async def read_wallet_identifiers(request: Request) -> tuple[str, ...] | None:
    requested_identifiers = read_list(request, ParamsList.WALLET_ID)
    if requested_identifiers is None:
        return None

    open_wallet_identifiers = {
        wallet.identifier for wallet in await fetch_open_wallets(request.user.id)
    }
    normalised_identifiers: list[str] = []
    for requested_identifier in requested_identifiers:
        normalised_identifier = normalised_uuid(requested_identifier)
        if normalised_identifier not in open_wallet_identifiers:
            raise invalid_parameter(
                ParamsList.WALLET_ID,
                DetailCode.WALLET_UNKNOWN,
                Messages.UNKNOWN_WALLET.format(wallet=requested_identifier),
            )
        if normalised_identifier not in normalised_identifiers:
            normalised_identifiers.append(normalised_identifier)

    return tuple(normalised_identifiers)


async def read_categories(request: Request) -> tuple[AnalyticsCategory | None, ...] | None:
    requested_tokens = read_list(request, ParamsList.CATEGORY)
    if requested_tokens is None:
        return None

    identifiers_by_token = {
        requested_token: normalised_uuid(requested_token)
        for requested_token in requested_tokens
        if requested_token != ReservedTokens.UNCATEGORISED
    }
    known_categories = await fetch_requested_categories(
        request.user.id,
        [identifier for identifier in identifiers_by_token.values() if identifier],
    )

    categories: list[AnalyticsCategory | None] = []
    for requested_token in requested_tokens:
        category = _requested_category(requested_token, identifiers_by_token, known_categories)
        if category not in categories:
            categories.append(category)

    return tuple(categories)


def _requested_category(
    requested_token: str,
    identifiers_by_token: dict[str, str | None],
    known_categories: dict[str, AnalyticsCategory],
) -> AnalyticsCategory | None:
    if requested_token == ReservedTokens.UNCATEGORISED:
        return None

    category = known_categories.get(identifiers_by_token[requested_token] or "")
    if category is None:
        raise invalid_parameter(
            ParamsList.CATEGORY,
            DetailCode.CATEGORY_UNKNOWN,
            Messages.UNKNOWN_CATEGORY.format(category=requested_token),
        )

    return category


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
