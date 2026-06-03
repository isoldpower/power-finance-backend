from ..dtos import TransactionDTO


def present_one(transaction: TransactionDTO) -> dict:
    return {
        "id": transaction.id,
        "wallet_id": transaction.wallet_id,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "meta": {
            "id": transaction.id,
            "occurred_at": transaction.occurred_at,
            "created_at": transaction.created_at,
        },
    }
