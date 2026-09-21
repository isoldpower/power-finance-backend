from decimal import Decimal
from typing import Any

from filter_grammar_py import Record

from ..aggregates import TransactionAggregate
from ..entities import TransactionEntity, WalletEntity


def transaction_subject(aggregate: TransactionAggregate, currency_code: str) -> Record:
    transaction = aggregate.root
    amount: Decimal = aggregate.amount

    subject: dict[str, Any] = {
        "wallet_id": str(transaction.container_id),
        "amount": amount,
        "currency": currency_code,
        "name": transaction.name,
        "type": str(TransactionEntity.type_for(amount)),
        "origin": str(transaction.origin),
        "created_at": transaction.created_at,
        "occurred_at": transaction.created_at,
    }

    if transaction.category:
        subject["category"] = transaction.category
    if transaction.chain_id:
        subject["chain_id"] = str(transaction.chain_id)

    return subject


def wallet_subject(wallet: WalletEntity, balance: Decimal) -> Record:
    return {
        "name": wallet.title,
        "currency": wallet.currency_code,
        "balance": balance,
        "created_at": wallet.created_at,
    }
