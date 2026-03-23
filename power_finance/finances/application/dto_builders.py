from finances.domain.entities import Transaction, Wallet, Webhook

from .dtos import (
    WalletDTO,
    TransactionDTO,
    TransactionParticipantDTO,
    TransactionPlainDTO,
    TransactionParticipantPlainDTO,
    WebhookDTO,
)


def wallet_to_dto(wallet: Wallet) -> WalletDTO:
    return WalletDTO(
        id=wallet.id,
        user_id=wallet.user_id,
        name=wallet.name,
        balance_amount=wallet.balance.amount,
        currency=wallet.balance.currency_code,
        credit=wallet.credit,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at,
    )

def transaction_to_dto(
    transaction: Transaction,
    sender_wallet: Wallet | None = None,
    receiver_wallet: Wallet | None = None,
) -> TransactionDTO:
    return TransactionDTO(
        id=transaction.id,
        sender=TransactionParticipantDTO(
            wallet=wallet_to_dto(sender_wallet),
            currency_code=transaction.sender.money.currency_code,
            amount=transaction.sender.money.amount,
        ) if transaction.sender and sender_wallet else None,
        receiver=TransactionParticipantDTO(
            wallet=wallet_to_dto(receiver_wallet),
            currency_code=transaction.receiver.money.currency_code,
            amount=transaction.receiver.money.amount,
        ) if transaction.receiver and receiver_wallet else None,
        description=transaction.description,
        created_at=transaction.created_at,
        type=transaction.type,
        category=transaction.category,
    )

def transaction_to_plain_dto(
    transaction: Transaction,
) -> TransactionPlainDTO:
    return TransactionPlainDTO(
        id=transaction.id,
        sender=TransactionParticipantPlainDTO(
            wallet_id=transaction.sender.wallet_id,
            currency_code=transaction.sender.money.currency_code,
            amount=transaction.sender.money.amount,
        ) if transaction.sender else None,
        receiver=TransactionParticipantPlainDTO(
            wallet_id=transaction.receiver.wallet_id,
            currency_code=transaction.receiver.money.currency_code,
            amount=transaction.receiver.money.amount,
        ) if transaction.receiver else None,
        description=transaction.description,
        created_at=transaction.created_at,
        type=transaction.type,
        category=transaction.category,
    )

def webhook_to_dto(webhook: Webhook) -> WebhookDTO:
    return WebhookDTO(
        id=webhook.id,
        title=webhook.title,
        url=webhook.url,
        subscribed_events=webhook.subscribed_events,
        secret=webhook.secret,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )