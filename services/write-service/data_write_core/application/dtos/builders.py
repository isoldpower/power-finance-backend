from decimal import Decimal
from uuid import UUID

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import (
    GoalEntity,
    MoneyFlowEntity,
    NotificationEntity,
    WalletEntity,
    WebhookEntity,
    WebhookSubscriptionEntity,
)
from data_write_core.domain.value_objects import (
    MoneyContainerKind,
    MoneyContainerRef,
)

from .goal_dto import GoalDTO, MoneyContainerDTO
from .notification_dto import NotificationDTO
from .transaction_dto import TransactionDTO, TransactionPlainDTO
from .wallet_dto import WalletDTO
from .webhook_dto import (
    WebhookDTO,
    WebhookSubscriptionDTO,
    WebhookWithSecretDTO,
)


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
        title=notification.title,
        body=notification.body,
        payload=notification.payload,
        severity=notification.severity,
        subject_type=notification.subject_type,
        subject_id=notification.subject_id,
        acknowledged_at=notification.acknowledged_at,
        created_at=notification.created_at,
        updated_at=notification.updated_at,
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


def goal_to_dto(goal: GoalEntity, progress: Decimal | None = None) -> GoalDTO:
    return GoalDTO(
        id=UUID(goal.unique_id),
        user_id=int(goal.user_id),
        name=goal.title,
        currency=goal.currency_code,
        target=goal.target,
        progress=progress if progress is not None else Decimal("0"),
        created_at=goal.created_at,
        updated_at=goal.updated_at,
        deleted_at=goal.deleted_at,
        finish_at=goal.finish_at,
        url=goal.url,
    )


def container_to_dto(container: MoneyContainerRef) -> MoneyContainerDTO:
    return MoneyContainerDTO(
        id=container.id,
        name=container.title,
        currency=container.currency_code,
        kind=container.kind,
    )


def wallet_dto_to_container(wallet: WalletDTO) -> MoneyContainerDTO:
    return MoneyContainerDTO(
        id=wallet.id,
        name=wallet.name,
        currency=wallet.currency,
        kind=MoneyContainerKind.WALLET,
    )


def transaction_to_dto(
    aggregate: TransactionAggregate,
    container: MoneyContainerDTO,
) -> TransactionDTO:
    return TransactionDTO(
        id=UUID(aggregate.unique_id),
        user_id=int(aggregate.root.user_id),
        name=aggregate.root.name,
        amount=abs(aggregate.amount),
        currency_code=container.currency,
        transaction_type=aggregate.type,
        origin=aggregate.root.origin,
        container=container,
        created_at=aggregate.root.created_at,
        updated_at=aggregate.root.updated_at,
        deleted_at=aggregate.root.deleted_at,
        category=aggregate.root.category,
        evidence_url=aggregate.root.evidence_url,
        chain_id=aggregate.root.chain_id,
    )


def transaction_to_plain_dto(
    transaction: MoneyFlowEntity,
    container: MoneyContainerDTO,
) -> TransactionPlainDTO:
    return TransactionPlainDTO(
        id=UUID(transaction.unique_id),
        amount=transaction.amount,
        container_id=str(container.id),
        currency_code=container.currency,
        created_at=transaction.created_at,
        transaction_id=transaction.transaction_id,
        cancels_other=transaction.cancels_other,
        adjusts_other=transaction.adjusts_other,
    )
