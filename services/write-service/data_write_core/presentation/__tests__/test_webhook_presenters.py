from datetime import datetime
from uuid import UUID

from data_write_core.application.dtos import (
    WebhookDTO,
    WebhookSubscriptionDTO,
    WebhookWithSecretDTO,
)
from data_write_core.presentation.http.presenters import WebhookHttpPresenter
from data_write_core.presentation.http.views.fallback_read._presenters import (
    present_webhook,
    present_webhook_subscription,
)

WEBHOOK_ID = UUID("1665b60e-bb7a-4360-8aa6-c1a578d81077")
SUBSCRIPTION_ID = UUID("b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92")
MOMENT = datetime(2026, 8, 12, 11, 51)


def make_webhook(enabled: bool = True) -> WebhookDTO:
    return WebhookDTO(
        id=WEBHOOK_ID,
        user_id=7,
        title="Ledger sync",
        url="https://hooks.example.com/finance/ledger",
        enabled=enabled,
        created_at=MOMENT,
        updated_at=MOMENT,
    )


def make_subscription() -> WebhookSubscriptionDTO:
    return WebhookSubscriptionDTO(
        id=SUBSCRIPTION_ID,
        webhook_id=WEBHOOK_ID,
        event_type="transaction.created",
        created_at=MOMENT,
    )


def test_endpoint_reports_enabled_and_no_deleted_at():
    """Webhooks are HARD deleted, so unlike every other resource here there is
    no `deleted_at` to report."""

    presented = WebhookHttpPresenter.present_one(make_webhook(enabled=False))

    assert presented["enabled"] is False
    assert "is_active" not in presented
    assert "deleted_at" not in presented


def test_the_secret_is_absent_from_a_plain_read():
    assert "secret" not in WebhookHttpPresenter.present_one(make_webhook())


def test_the_secret_is_present_only_on_creation_and_rotation():
    with_secret = WebhookWithSecretDTO(
        id=WEBHOOK_ID,
        user_id=7,
        title="Ledger sync",
        url="https://hooks.example.com/finance/ledger",
        enabled=True,
        created_at=MOMENT,
        updated_at=MOMENT,
        secret="whsec_9f2b1c7e",
    )

    assert WebhookHttpPresenter.present_with_secret(with_secret)["secret"] == "whsec_9f2b1c7e"


def test_subscription_carries_event_and_nothing_it_does_not_have():
    presented = WebhookHttpPresenter.present_subscription(make_subscription())

    assert presented["event"] == "transaction.created"
    assert set(presented) == {"id", "webhook_id", "event", "created_at"}


def test_the_fallback_shape_matches_the_primary_one():
    """The gateway can reroute mid-session, so a client must not be able to
    tell which side answered."""

    assert present_webhook(make_webhook()) == WebhookHttpPresenter.present_one(make_webhook())
    assert present_webhook_subscription(make_subscription()) == (
        WebhookHttpPresenter.present_subscription(make_subscription())
    )
