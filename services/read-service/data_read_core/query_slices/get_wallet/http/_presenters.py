from decimal import Decimal

from data_read_core.shared.money import money_at_scale

from ..dtos import RecentTransactionDTO, WalletDetailDTO


async def present_one(
    detail: WalletDetailDTO,
    recent: list[RecentTransactionDTO] | None = None,
) -> dict:
    wallet = detail.wallet
    currency = wallet.currency

    return {
        "id": wallet.id,
        "name": wallet.name,
        "created_at": wallet.created_at,
        "updated_at": wallet.updated_at,
        "deleted_at": wallet.deleted_at,
        "category": wallet.category,
        "currency": currency,
        "money": await money_at_scale(
            wallet.balance_amount,
            currency,
        ),
        "zero_balance": await money_at_scale(
            wallet.zero_balance_amount,
            currency,
        ),
        "favorite": wallet.favorite,
        "color": wallet.color,
        "period": {
            "inflow": await money_at_scale(
                detail.period.inflow,
                currency,
            ),
            "outflow": await money_at_scale(
                detail.period.outflow,
                currency,
            ),
        },
        "recent": [
            await _present_recent(row) for row in (detail.recent if recent is None else recent)
        ],
    }


async def _present_recent(transaction: RecentTransactionDTO) -> dict:
    return {
        "id": transaction.id,
        "name": transaction.name,
        "created_at": transaction.created_at,
        "updated_at": transaction.updated_at,
        "deleted_at": transaction.deleted_at,
        "money": await money_at_scale(
            abs(Decimal(transaction.amount)),
            transaction.currency,
        ),
        "type": ("expense" if Decimal(transaction.amount) < 0 else "income"),
        "origin": transaction.origin,
        "wallet": {
            "id": transaction.wallet_id,
            "name": transaction.wallet_name,
        },
        "category": transaction.category,
        "chain_id": transaction.chain_id,
    }
