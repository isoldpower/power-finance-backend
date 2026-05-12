import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from finances.domain.entities import Transaction, Wallet, Webhook

from .dtos import (
    WalletDTO,
    TransactionDTO,
    TransactionPlainDTO,
    WebhookDTO,
)


def wallet_to_dto(wallet: Wallet) -> WalletDTO:
    return WalletDTO(
        id=wallet.id,
        user_id=wallet.user_id,
        name=wallet.name,
        balance_amount=wallet.balance,
        currency=wallet.currency_code,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at,
    )

def transaction_to_dto(
    transaction: Transaction,
    source_wallet: WalletDTO,
) -> TransactionDTO:
    return TransactionDTO(
        id=transaction.id,
        amount=transaction.amount,
        source_wallet=source_wallet,
        currency_code=source_wallet.currency,
        created_at=transaction.created_at,
    )

def transaction_to_plain_dto(
    transaction: Transaction,
    source_wallet: WalletDTO,
) -> TransactionPlainDTO:
    return TransactionPlainDTO(
        id=transaction.id,
        amount=transaction.amount,
        source_wallet_id=str(source_wallet.id),
        currency_code=source_wallet.currency,
        created_at=transaction.created_at,
    )

def webhook_to_dto(webhook: Webhook) -> WebhookDTO:
    return WebhookDTO(
        id=webhook.id,
        title=webhook.title,
        url=webhook.url,
        secret=webhook.secret,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


def serialize_wallet_dto(dto: WalletDTO) -> str:
    return json.dumps({
        'id': str(dto.id),
        'user_id': dto.user_id,
        'name': dto.name,
        'balance_amount': str(dto.balance_amount),
        'currency': dto.currency,
        'created_at': dto.created_at.isoformat(),
        'updated_at': dto.updated_at.isoformat(),
    })


def deserialize_wallet_dto(raw: str) -> WalletDTO:
    d = json.loads(raw)
    return WalletDTO(
        id=UUID(d['id']),
        user_id=d['user_id'],
        name=d['name'],
        balance_amount=Decimal(d['balance_amount']),
        currency=d['currency'],
        created_at=datetime.fromisoformat(d['created_at']),
        updated_at=datetime.fromisoformat(d['updated_at']),
    )