"""What the worker subscribes to.

The plans themselves are covered by the effect tests; what this file protects
is that an effect written and then never wired up fails loudly here rather than
silently in production.
"""

import pytest
from kafka_consumer_py import KafkaEventRouter
from kafka_consumer_py.exceptions import HandlerNotFoundError

from background_workers.services.build_event_router import _subscribe_all_events


def _router() -> KafkaEventRouter:
    router = KafkaEventRouter()
    _subscribe_all_events(router)
    return router


def test_every_subscribed_event_is_registered():
    assert sorted(_router().registered_event_types()) == [
        "TransactionCreated",
        "TransactionDeleted",
        "TransactionUpdated",
        "UserSynced",
    ]


def test_user_synced_is_subscribed_so_accounts_exist_before_a_dispatch():
    """A dispatch reads the chart of accounts and never extends it, so dropping
    this subscription would break every first transaction."""

    assert _router().has("UserSynced") is True


def test_metadata_updates_are_deliberately_not_subscribed():
    """A changed name or category does not change what the legs are worth, so
    there is nothing to re-derive."""

    assert _router().has("TransactionMetadataUpdated") is False


async def test_an_unsubscribed_event_is_refused_rather_than_ignored():
    from kafka_consumer_py.fakes import make_event
    from kafka_messages import WalletCreated

    with pytest.raises(HandlerNotFoundError):
        await _router().dispatch(make_event(WalletCreated()))
