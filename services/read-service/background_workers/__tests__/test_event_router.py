import pytest
from kafka_consumer_py import KafkaEventRouter

from background_workers.services.build_event_router import _subscribe_all_events
from background_workers.services.build_event_router._types import ProjectionRouters

ACCOUNT_EVENT_TYPES = {
    "AccountCreated",
    "AccountUpdated",
    "AccountPostingCreated",
    "AccountPostingDeleted",
    "AccountPostingsDispatched",
}

SEARCH_INDEXED_EVENT_TYPES = {
    "WalletCreated",
    "WalletUpdated",
    "WalletDeleted",
    "GoalCreated",
    "GoalUpdated",
    "GoalDeleted",
    "TransactionCreated",
    "TransactionUpdated",
    "TransactionDeleted",
    "TransactionMetadataUpdated",
    "AutomationCreated",
    "AutomationUpdated",
    "AutomationDeleted",
    "AutomationRan",
}


@pytest.fixture
def lanes() -> ProjectionRouters:
    routers = ProjectionRouters(postgres=KafkaEventRouter(), search=KafkaEventRouter())
    _subscribe_all_events(routers)

    return routers


@pytest.fixture
def registered(lanes: ProjectionRouters) -> set[str]:
    return set(lanes.postgres.registered_event_types())


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


def test_only_indexed_events_reach_the_search_lane(lanes: ProjectionRouters):
    assert set(lanes.search.registered_event_types()) == SEARCH_INDEXED_EVENT_TYPES


def test_every_indexed_event_is_also_projected_into_postgres(lanes: ProjectionRouters):
    assert set(lanes.postgres.registered_event_types()) >= SEARCH_INDEXED_EVENT_TYPES
