from collections.abc import Mapping
from decimal import Decimal

from data_read_core.shared.chains import present_chain
from data_read_core.shared.money import money_at_scale

from ..dtos import TransactionDTO
from ..infra import count_chain_members


async def present_one(
    transaction: TransactionDTO,
    chain_sizes: Mapping[str, int],
) -> dict:
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
        "chain": present_chain(transaction.chain_id, chain_sizes),
    }


async def present_many(transactions: list[TransactionDTO]) -> list[dict]:
    chain_sizes = await count_chain_members(transaction.chain_id for transaction in transactions)

    return [await present_one(transaction, chain_sizes) for transaction in transactions]
