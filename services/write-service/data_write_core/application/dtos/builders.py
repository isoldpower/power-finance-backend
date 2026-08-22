from decimal import Decimal
from uuid import UUID

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import (
    MoneyFlowEntity,
    NotificationEntity,
    WalletEntity,
    WebhookEntity,
    WebhookSubscriptionEntity,
)

from .notification_dto import NotificationDTO
from .transaction_dto import TransactionDTO, TransactionPlainDTO
from .wallet_dto import WalletDTO
from .webhook_dto import WebhookDTO, WebhookSubscriptionDTO, WebhookWithSecretDTO


def webhook_to_dto(webhook: WebhookEntity) -> WebhookDTO:
    return WebhookDTO(
        id=UUID(webhook.unique_id),
        user_id=int(webhook.user_id),
        title=webhook.title,
        url=webhook.url,
        is_active=webhook.is_active,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


def webhook_to_secret_dto(webhook: WebhookEntity) -> WebhookWithSecretDTO:
    return WebhookWithSecretDTO(
        id=UUID(webhook.unique_id),
        user_id=int(webhook.user_id),
        title=webhook.title,
        url=webhook.url,
        is_active=webhook.is_active,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
        secret=webhook.secret,
    )


def webhook_subscription_to_dto(
    subscription: WebhookSubscriptionEntity,
) -> WebhookSubscriptionDTO:
    return WebhookSubscriptionDTO(
        id=UUID(subscription.unique_id),
        webhook_id=UUID(subscription.webhook_id),
        event_type=subscription.event_type,
        is_active=subscription.is_active,
        created_at=subscription.created_at,
    )


def notification_to_dto(notification: NotificationEntity) -> NotificationDTO:
    return NotificationDTO(
        id=UUID(notification.unique_id),
        user_id=int(notification.user_id),
        short=notification.short,
        message=notification.message,
        payload=notification.payload,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


def wallet_to_dto(wallet: WalletEntity, balance_amount: Decimal | None = None) -> WalletDTO:
    return WalletDTO(
        id=UUID(wallet.unique_id),
        user_id=int(wallet.user_id),
        name=wallet.title,
        balance_amount=balance_amount if balance_amount is not None else Decimal("0"),
        currency=wallet.currency_code,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at,
        category=wallet.category,
        color=wallet.color,
        favorite=wallet.favorite,
        zero_balance=wallet.zero_balance,
        deleted_at=wallet.deleted_at,
    )


def transaction_to_dto(
    aggregate: TransactionAggregate,
    wallet: WalletDTO,
) -> TransactionDTO:
    return TransactionDTO(
        id=UUID(aggregate.unique_id),
        user_id=int(aggregate.root.user_id),
        name=aggregate.root.name,
        amount=abs(aggregate.amount),
        currency_code=wallet.currency,
        transaction_type=aggregate.type,
        origin=aggregate.root.origin,
        wallet=wallet,
        created_at=aggregate.root.created_at,
        updated_at=aggregate.root.updated_at,
        deleted_at=aggregate.root.deleted_at,
        category=aggregate.root.category,
        evidence_url=aggregate.root.evidence_url,
        chain_id=aggregate.root.chain_id,
    )


def transaction_to_plain_dto(
    transaction: MoneyFlowEntity,
    source_wallet: WalletDTO,
) -> TransactionPlainDTO:
    return TransactionPlainDTO(
        id=UUID(transaction.unique_id),
        amount=transaction.amount,
        source_wallet_id=str(source_wallet.id),
        currency_code=source_wallet.currency,
        created_at=transaction.created_at,
        transaction_id=transaction.transaction_id,
        cancels_other=transaction.cancels_other,
        adjusts_other=transaction.adjusts_other,
    )
