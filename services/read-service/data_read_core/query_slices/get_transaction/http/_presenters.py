from decimal import Decimal

from data_read_core.shared.money import money_at_scale

from ..dtos import TransactionDTO


async def present_one(transaction: TransactionDTO) -> dict:
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
        "evidence": ({"url": transaction.evidence_url} if transaction.evidence_url else None),
        "postings": [],
        "analysis": None,
    }
