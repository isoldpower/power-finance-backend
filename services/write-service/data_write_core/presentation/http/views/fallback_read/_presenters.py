from datetime import datetime

from data_write_core.application.dtos import (
    NotificationDTO,
    TransactionPlainDTO,
    WalletDTO,
    WebhookDTO,
    WebhookSubscriptionDTO,
)


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


def present_webhook(webhook: WebhookDTO) -> dict:
    return {
        "id": str(webhook.id),
        "title": webhook.title,
        "url": webhook.url,
        "is_active": webhook.is_active,
        "meta": {
            "id": str(webhook.id),
            "created_at": _iso(webhook.created_at),
            "updated_at": _iso(webhook.updated_at),
        },
    }


def present_webhooks(webhooks: list[WebhookDTO]) -> list[dict]:
    return [present_webhook(webhook) for webhook in webhooks]


def present_webhook_subscription(subscription: WebhookSubscriptionDTO) -> dict:
    return {
        "id": str(subscription.id),
        "webhook_id": str(subscription.webhook_id),
        "event_type": subscription.event_type,
        "is_active": subscription.is_active,
        "created_at": _iso(subscription.created_at),
    }


def present_webhook_subscriptions(
    subscriptions: list[WebhookSubscriptionDTO],
) -> list[dict]:
    return [present_webhook_subscription(subscription) for subscription in subscriptions]


def present_notification(notification: NotificationDTO) -> dict:
    return {
        "id": str(notification.id),
        "short": notification.short,
        "message": notification.message,
        "payload": notification.payload,
        "is_read": notification.is_read,
        "created_at": _iso(notification.created_at),
    }


def present_notifications(notifications: list[NotificationDTO]) -> list[dict]:
    return [present_notification(notification) for notification in notifications]
