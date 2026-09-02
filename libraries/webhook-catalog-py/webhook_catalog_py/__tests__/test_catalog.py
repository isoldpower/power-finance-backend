from webhook_catalog_py import (
    event_for_outbox_type,
    event_types,
    event_values,
    is_known_event,
)


def test_every_event_is_deliverable():
    for entry in event_types():
        assert entry.outbox_types, f"{entry.event} is subscribable but nothing publishes it"


def test_events_are_unique():
    events = [entry.event for entry in event_types()]

    assert len(events) == len(set(events))


def test_outbox_types_map_to_one_event_each():
    seen: dict[str, str] = {}
    for entry in event_types():
        for outbox_type in entry.outbox_types:
            assert outbox_type not in seen
            seen[outbox_type] = entry.event


def test_subject_matches_the_event_prefix():
    for entry in event_types():
        assert entry.event.startswith(f"{entry.subject}.")


def test_known_event_lookup():
    assert is_known_event("transaction.created")
    assert not is_known_event("transaction.exploded")


def test_metadata_updates_publish_as_transaction_updated():
    assert event_for_outbox_type("TransactionMetadataUpdated") == "transaction.updated"
    assert event_for_outbox_type("TransactionUpdated") == "transaction.updated"


def test_unpublished_outbox_types_have_no_event():
    assert event_for_outbox_type("WalletDeleted") is None


def test_event_values_matches_the_catalog():
    assert event_values() == {entry.event for entry in event_types()}
