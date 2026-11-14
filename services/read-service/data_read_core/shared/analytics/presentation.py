from datetime import UTC, datetime
from decimal import Decimal

from data_read_core.shared.money import money_at_scale
from data_read_core.shared.timestamps import to_iso

from .ledger_rows import LedgerWallet
from .scope import AnalyticsScope
from .transaction_briefs import TransactionBriefDTO


def present_scope_meta(scope: AnalyticsScope, cached: bool, **report_meta: object) -> dict:
    return {
        "since": to_iso(scope.window.since),
        "until": to_iso(scope.window.until),
        "currency": scope.currency,
        "timezone": scope.timezone,
        "wallet_ids": list(scope.wallet_identifiers) if scope.wallet_identifiers else None,
        "categories": scope.category_tokens,
        "generated_at": to_iso(datetime.now(UTC)),
        "cached": cached,
        **report_meta,
    }


def present_collection_meta(
    scope: AnalyticsScope,
    cached: bool,
    limit: int,
    total: int,
    **report_meta: object,
) -> dict:
    return present_scope_meta(
        scope,
        cached,
        limit=limit,
        total=total,
        next_cursor=None,
        prev_cursor=None,
        **report_meta,
    )


def present_wallet_reference(wallet: LedgerWallet) -> dict:
    return {
        "id": wallet.identifier,
        "name": wallet.name,
        "color": wallet.color,
    }


def present_wallet_option(wallet: LedgerWallet) -> dict:
    return {
        **present_wallet_reference(wallet),
        "currency": wallet.currency,
    }


async def present_transaction_brief(brief: TransactionBriefDTO, currency: str) -> dict:
    return {
        "id": brief.identifier,
        "name": brief.name,
        "created_at": to_iso(brief.created_at),
        "type": brief.side.value,
        "category": brief.category,
        "wallet": present_wallet_reference(brief.wallet),
        "money": await money_at_scale(brief.native_amount, brief.native_currency),
        "converted": await money_at_scale(brief.converted_amount, currency),
    }


async def present_optional_transaction_brief(
    brief: TransactionBriefDTO | None,
    currency: str,
) -> dict | None:
    if brief is None:
        return None

    return await present_transaction_brief(brief, currency)


def as_percentage(percentage: Decimal | None) -> float | None:
    if percentage is None:
        return None

    return float(percentage)
