"""What the consumer is subscribed to.

Registration is pure wiring: nothing fails at import time when a handler is
left out of `_KNOWN_HANDLERS`, the events simply stop being projected. These
assertions are the only thing standing between that and silence.
"""

import pytest
from kafka_consumer_py import KafkaEventRouter

from background_workers.services.build_event_router import _subscribe_all_events

ACCOUNT_EVENT_TYPES = {
    "AccountCreated",
    "AccountUpdated",
    "AccountPostingCreated",
    "AccountPostingDeleted",
    "AccountPostingsDispatched",
}


@pytest.fixture
def registered() -> set[str]:
    router = KafkaEventRouter()
    _subscribe_all_events(router)

    return set(router.registered_event_types())


def test_every_account_event_ai_service_publishes_is_consumed(registered):
    assert registered >= ACCOUNT_EVENT_TYPES


def test_the_write_service_events_are_still_consumed(registered):
    assert {
        "UserSynced",
        "WalletCreated",
        "TransactionCreated",
        "TransactionUpdated",
        "TransactionDeleted",
    } <= registered
