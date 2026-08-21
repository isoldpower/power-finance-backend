from data_read_core.shared.money import amount_at_scale

from ..dtos import TransactionDTO


async def present_one(transaction: TransactionDTO) -> dict:
    return {
        "id": transaction.id,
        "wallet_id": transaction.wallet_id,
        "amount": await amount_at_scale(transaction.amount, transaction.currency),
        "currency": transaction.currency,
        "occurred_at": transaction.occurred_at,
        "created_at": transaction.created_at,
        "updated_at": None,
        "deleted_at": None,
    }
