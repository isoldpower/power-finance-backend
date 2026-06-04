"""Response shaping for the fallback-read routes.

These deliberately mirror the Read Service's payloads (``data_read_core``'s
``_presenters``) rather than the write side's command responses, so the gateway
can swap a 507'd read for a fallback read transparently — the client sees the
same object shape either way.
"""

from datetime import datetime

from data_write_core.application.dtos import TransactionPlainDTO, WalletDTO


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def present_wallet(wallet: WalletDTO) -> dict:
    return {
        "id": str(wallet.id),
        "name": wallet.name,
        "balance": {
            "amount": str(wallet.balance_amount),
            "currency": wallet.currency,
        },
        "meta": {
            "id": str(wallet.id),
            "created_at": _iso(wallet.created_at),
            "updated_at": _iso(wallet.updated_at),
        },
    }


def present_wallets(wallets: list[WalletDTO]) -> list[dict]:
    return [present_wallet(wallet) for wallet in wallets]


def present_transaction(transaction: TransactionPlainDTO) -> dict:
    return {
        "id": str(transaction.id),
        "wallet_id": str(transaction.source_wallet_id),
        "amount": str(transaction.amount),
        "currency": transaction.currency_code,
        "meta": {
            "id": str(transaction.id),
            "occurred_at": _iso(transaction.created_at),
            "created_at": _iso(transaction.created_at),
        },
    }


def present_transactions(transactions: list[TransactionPlainDTO]) -> list[dict]:
    return [present_transaction(transaction) for transaction in transactions]
