import io
import sys
from contextlib import redirect_stdout

import pytest
from data_read_core.shared.kafka_dedupe import KafkaConsumedEvent
from django.core.management import call_command

BASELINE_GROUP = "read-service.write-consumer"
APPLIED = "aaaaaaaa-0000-0000-0000-000000000001"
SKIPPED = "bbbbbbbb-0000-0000-0000-000000000002"


def _run(event_ids, **options) -> str:
    output = io.StringIO()
    original_stdin = sys.stdin
    sys.stdin = io.StringIO("\n".join(event_ids))
    try:
        with redirect_stdout(output):
            call_command("forget_consumed_events", stdout=output, **options)
    finally:
        sys.stdin = original_stdin

    return output.getvalue()


@pytest.fixture
def _consumed(db):
    KafkaConsumedEvent.objects.bulk_create(
        [
            KafkaConsumedEvent(consumer_group=BASELINE_GROUP, event_id=APPLIED),
            KafkaConsumedEvent(consumer_group=BASELINE_GROUP, event_id=SKIPPED),
            KafkaConsumedEvent(consumer_group="ai-service.dispatcher", event_id=SKIPPED),
        ]
    )


def test_only_the_listed_event_is_forgotten(_consumed):
    _run([SKIPPED])

    remaining = set(
        KafkaConsumedEvent.objects.filter(consumer_group=BASELINE_GROUP).values_list(
            "event_id", flat=True
        )
    )

    assert remaining == {APPLIED}


def test_another_services_row_for_the_same_event_is_left_alone(_consumed):
    _run([SKIPPED])

    assert KafkaConsumedEvent.objects.filter(
        consumer_group="ai-service.dispatcher",
        event_id=SKIPPED,
    ).exists()


def test_a_dry_run_deletes_nothing(_consumed):
    output = _run([SKIPPED], dry_run=True)

    assert KafkaConsumedEvent.objects.filter(event_id=SKIPPED).count() == 2
    assert "would forget 1 of 1" in output


def test_an_event_the_group_never_saw_is_reported_as_unmatched(_consumed):
    output = _run([SKIPPED, "cccccccc-0000-0000-0000-000000000003"])

    assert "forgot 1 of 2" in output


def test_empty_input_is_refused(db):
    with pytest.raises(Exception, match="No event ids"):
        _run([])
