from write_service.common.timestamps import to_iso

from data_write_core.application.dtos import (
    ActionDTO,
    AutomationDTO,
    NotificationDTO,
    TransactionDTO,
    WalletDTO,
    WebhookDTO,
    WebhookSubscriptionDTO,
)
from data_write_core.application.money_scales import money_at_scale
from data_write_core.application.queries import (
    FallbackNotificationCounts,
    FallbackWalletDetail,
)

from ...presenters import (
    ActionHttpPresenter,
    AutomationHttpPresenter,
    NotificationHttpPresenter,
    TransactionHttpPresenter,
    WebhookHttpPresenter,
)


async def present_wallet(wallet: WalletDTO) -> dict:
    return {
        "id": str(wallet.id),
        "name": wallet.name,
        "created_at": to_iso(wallet.created_at),
        "updated_at": to_iso(wallet.updated_at),
        "deleted_at": to_iso(wallet.deleted_at),
        "category": wallet.category,
        "currency": wallet.currency,
        "money": await money_at_scale(
            wallet.balance_amount,
            wallet.currency,
        ),
        "zero_balance": await money_at_scale(
            wallet.zero_balance,
            wallet.currency,
        ),
        "favorite": wallet.favorite,
        "color": wallet.color,
    }


async def present_wallets(wallets: list[WalletDTO]) -> list[dict]:
    return [await present_wallet(wallet) for wallet in wallets]


async def present_wallet_detail(detail: FallbackWalletDetail) -> dict:
    currency = detail.wallet.currency

    return {
        **await present_wallet(detail.wallet),
        "period": {
            "inflow": await money_at_scale(
                detail.inflow,
                currency,
            ),
            "outflow": await money_at_scale(
                detail.outflow,
                currency,
            ),
        },
    }


async def present_transaction(transaction: TransactionDTO) -> dict:
    return await TransactionHttpPresenter.present_one(transaction)


async def present_transactions(transactions: list[TransactionDTO]) -> list[dict]:
    return [await present_transaction(transaction) for transaction in transactions]


def present_webhook(webhook: WebhookDTO) -> dict:
    return WebhookHttpPresenter.present_one(webhook)


def present_webhooks(webhooks: list[WebhookDTO]) -> list[dict]:
    return [present_webhook(webhook) for webhook in webhooks]


def present_webhook_subscription(subscription: WebhookSubscriptionDTO) -> dict:
    return WebhookHttpPresenter.present_subscription(subscription)


def present_webhook_subscriptions(
    subscriptions: list[WebhookSubscriptionDTO],
) -> list[dict]:
    return [present_webhook_subscription(subscription) for subscription in subscriptions]


def present_notification(notification: NotificationDTO) -> dict:
    return NotificationHttpPresenter.present_one(notification)


def present_notifications(notifications: list[NotificationDTO]) -> list[dict]:
    return [present_notification(notification) for notification in notifications]


def present_notification_counts(counts: FallbackNotificationCounts) -> dict:
    return {
        "unacknowledged": counts.unacknowledged,
        "total": counts.total,
    }


def present_action(action: ActionDTO) -> dict:
    return ActionHttpPresenter.present_one(action)


def present_actions(actions: list[ActionDTO]) -> list[dict]:
    return [present_action(action) for action in actions]


def present_automation(automation: AutomationDTO) -> dict:
    return AutomationHttpPresenter.present_one(automation)


def present_automations(automations: list[AutomationDTO]) -> list[dict]:
    return [present_automation(automation) for automation in automations]
