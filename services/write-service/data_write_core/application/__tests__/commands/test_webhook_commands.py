from datetime import datetime
from uuid import UUID

import pytest
from webhook_catalog_py import event_values

from data_write_core.application.commands import (
    AddWebhookSubscriptionCommand,
    AddWebhookSubscriptionCommandHandler,
)
from data_write_core.domain.entities import WebhookEntity
from data_write_core.domain.exceptions import (
    DuplicateWebhookSubscriptionError,
    UnsupportedWebhookEventTypeError,
)

WEBHOOK_A = "11111111-1111-1111-1111-111111111111"


def make_webhook(webhook_id: str) -> WebhookEntity:
    moment = datetime(2026, 1, 1)
    return WebhookEntity(
        id=webhook_id,
        title="Hook",
        url="https://example.com/hook",
        secret="secret",
        user_id="7",
        created_at=moment,
        updated_at=moment,
    )


class FakeWebhookRepository:
    def __init__(self, webhooks: list[WebhookEntity], existing_subscriptions=()) -> None:
        self._webhooks = {str(webhook.unique_id): webhook for webhook in webhooks}
        self._existing = set(existing_subscriptions)

    async def get_user_webhook_by_id(self, webhook_id, user_id):
        webhook = self._webhooks.get(str(webhook_id))
        if webhook is None:
            raise LookupError(f"webhook {webhook_id} not found")
        return webhook

    async def subscription_exists(self, webhook_id, event_type):
        return (str(webhook_id), event_type) in self._existing


async def test_subscribe_rejects_unsupported_event_type():
    handler = AddWebhookSubscriptionCommandHandler(
        webhook_repository=FakeWebhookRepository([make_webhook(WEBHOOK_A)]),
        outbox_repository=object(),
    )

    with pytest.raises(UnsupportedWebhookEventTypeError):
        await handler.handle(
            AddWebhookSubscriptionCommand(
                user_id=7,
                user_external_id="user_abc",
                webhook_id=UUID(WEBHOOK_A),
                event_type="wallet.exploded",
            )
        )


async def test_subscribe_rejects_duplicate_subscription():
    handler = AddWebhookSubscriptionCommandHandler(
        webhook_repository=FakeWebhookRepository(
            [make_webhook(WEBHOOK_A)],
            existing_subscriptions={(WEBHOOK_A, "transaction.created")},
        ),
        outbox_repository=object(),
    )

    with pytest.raises(DuplicateWebhookSubscriptionError):
        await handler.handle(
            AddWebhookSubscriptionCommand(
                user_id=7,
                user_external_id="user_abc",
                webhook_id=UUID(WEBHOOK_A),
                event_type="transaction.created",
            )
        )


async def test_subscribe_accepts_every_event_in_the_shared_catalog():
    """The catalog GET /webhooks/event-types serves and the one the validator
    checks against are the same table, so nothing can be advertised as
    subscribable and then refused here."""

    for event in event_values():
        handler = AddWebhookSubscriptionCommandHandler(
            webhook_repository=FakeWebhookRepository(
                [make_webhook(WEBHOOK_A)],
                existing_subscriptions={(WEBHOOK_A, event)},
            ),
            outbox_repository=object(),
        )

        # Reaching the duplicate check means the event type was accepted.
        with pytest.raises(DuplicateWebhookSubscriptionError):
            await handler.handle(
                AddWebhookSubscriptionCommand(
                    user_id=7,
                    user_external_id="user_abc",
                    webhook_id=UUID(WEBHOOK_A),
                    event_type=event,
                )
            )
