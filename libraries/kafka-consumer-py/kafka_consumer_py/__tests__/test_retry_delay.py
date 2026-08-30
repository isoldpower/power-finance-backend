"""Holding a partition back until a retried message is due.

The loop runs against a fake consumer that records what was seeked, paused and
resumed, because those three calls are the whole mechanism: a message that is
not due is rewound and its partition parked, and nothing behind it runs in the
meantime.
"""

import asyncio
from datetime import UTC, datetime, timedelta

from aiokafka.structs import TopicPartition
from kafka_client_py import headers as Headers

from kafka_consumer_py.kafka_consumer import KafkaConsumerLoop
from kafka_consumer_py.retry_delay import DeferredPartitions, retry_due_at

RETRY = TopicPartition("events.retry", 0)
ASYNC = TopicPartition("events.async", 0)


def _in(seconds: float) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=seconds)


def _ago(seconds: float) -> datetime:
    return datetime.now(UTC) - timedelta(seconds=seconds)


class _Record:
    def __init__(
        self,
        offset: int,
        *,
        due_at: datetime | None = None,
        topic: str = "events.retry",
        retry_at_header: bytes | None = None,
    ) -> None:
        self.topic = topic
        self.partition = 0
        self.offset = offset
        if retry_at_header is not None:
            self.headers = [(Headers.HEADER_RETRY_AT, retry_at_header)]
        elif due_at is not None:
            self.headers = [(Headers.HEADER_RETRY_AT, Headers.encode(due_at))]
        else:
            self.headers = []


class _Signal:
    """A shutdown signal that only fires when asked.

    `wait()` has to block until then: the loop races it against each unit of
    work, so a signal that resolves immediately would cancel every message
    before it was handled.
    """

    def __init__(self) -> None:
        self._stop = False
        self._event = asyncio.Event()

    def is_stop_requested(self) -> bool:
        return self._stop

    def request_stop(self) -> None:
        self._stop = True
        self._event.set()

    def install(self) -> None: ...

    async def wait(self) -> None:
        await self._event.wait()


class _FakeConsumer:
    """Serves prepared batches one poll at a time, then keeps returning empty
    ones until it has idled enough, and stops the loop itself."""

    def __init__(self, batches, signal: _Signal, *, idle_polls: int = 0) -> None:
        self._batches = list(batches)
        self._signal = signal
        self._idle_polls = idle_polls
        self.seeks: list[tuple[TopicPartition, int]] = []
        self.paused: list[TopicPartition] = []
        self.resumed: list[TopicPartition] = []
        self.commits = 0
        self.assigned = {RETRY, ASYNC}

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def getmany(self, timeout_ms: int = 0):
        if self._batches:
            return self._batches.pop(0)
        if self._idle_polls > 0:
            self._idle_polls -= 1
            await asyncio.sleep(0.05)
            return {}
        self._signal.request_stop()
        return {}

    def seek(self, topic_partition, offset) -> None:
        self.seeks.append((topic_partition, offset))

    def pause(self, topic_partition) -> None:
        self.paused.append(topic_partition)

    def resume(self, topic_partition) -> None:
        self.resumed.append(topic_partition)

    def assignment(self):
        return self.assigned

    async def commit(self) -> None:
        self.commits += 1


class _RecordingHandler:
    def __init__(self) -> None:
        self.handled: list[int] = []

    async def handle(self, record) -> None:
        self.handled.append(record.offset)


async def _run(batches, *, idle_polls: int = 0):
    signal = _Signal()
    consumer = _FakeConsumer(batches, signal, idle_polls=idle_polls)
    handler = _RecordingHandler()
    loop = KafkaConsumerLoop(consumer, handler, signal, poll_timeout_ms=10)  # type: ignore[arg-type]

    await asyncio.wait_for(loop.run(), timeout=10)

    return consumer, handler


async def test_a_message_that_is_not_due_is_rewound_and_its_partition_paused():
    consumer, handler = await _run([{RETRY: [_Record(7, due_at=_in(30))]}])

    assert handler.handled == []
    assert consumer.seeks == [(RETRY, 7)]
    assert consumer.paused == [RETRY]


async def test_a_message_whose_time_has_passed_is_handled_normally():
    consumer, handler = await _run([{RETRY: [_Record(7, due_at=_ago(30))]}])

    assert handler.handled == [7]
    assert consumer.paused == []
    assert consumer.seeks == []


async def test_a_message_with_no_retry_header_is_due_now():
    consumer, handler = await _run([{RETRY: [_Record(7)]}])

    assert handler.handled == [7]
    assert consumer.paused == []


async def test_nothing_behind_a_held_message_is_handled_first():
    """The rewind puts the partition back to the held offset, so handling a
    later record would mean handling it twice once the partition resumes."""

    batch = {RETRY: [_Record(7, due_at=_in(30)), _Record(8), _Record(9)]}

    consumer, handler = await _run([batch])

    assert handler.handled == []
    assert consumer.seeks == [(RETRY, 7)]


async def test_other_partitions_keep_moving_while_one_is_held():
    """The reason for pausing rather than sleeping: one undue message must not
    stall the whole consumer."""

    batch = {
        RETRY: [_Record(7, due_at=_in(30))],
        ASYNC: [_Record(1, topic="events.async"), _Record(2, topic="events.async")],
    }

    consumer, handler = await _run([batch])

    assert handler.handled == [1, 2]
    assert consumer.paused == [RETRY]


async def test_a_held_partition_is_resumed_once_its_message_comes_due():
    consumer, _ = await _run([{RETRY: [_Record(7, due_at=_in(0.2))]}], idle_polls=20)

    assert consumer.paused == [RETRY]
    assert consumer.resumed == [RETRY]


async def test_a_partition_taken_away_while_held_is_not_resumed():
    """A rebalance can move a held partition. Resuming one this consumer no
    longer owns would raise, and its new owner starts from the same offset."""

    signal = _Signal()
    consumer = _FakeConsumer([], signal)
    consumer.assigned = set()
    loop = KafkaConsumerLoop(consumer, _RecordingHandler(), signal)  # type: ignore[arg-type]
    loop._deferred.hold(RETRY, _ago(1))

    loop._resume_due_partitions()

    assert consumer.resumed == []
    assert RETRY not in loop._deferred


async def test_a_held_message_is_not_committed_past():
    """Committing would lose the message: the position must stay at the record
    that was held, not move beyond it."""

    consumer, _ = await _run([{RETRY: [_Record(7, due_at=_in(30))]}])

    assert consumer.commits == 0


def test_the_registry_only_reports_partitions_whose_time_has_come():
    deferred = DeferredPartitions()
    deferred.hold(RETRY, _in(60))
    deferred.hold(ASYNC, _ago(1))

    assert deferred.due(datetime.now(UTC)) == [ASYNC]
    assert len(deferred) == 2


def test_an_unreadable_retry_header_reads_as_due_now():
    """Parking a message forever because its own header is corrupt would be the
    worst of both behaviours."""

    assert retry_due_at([(Headers.HEADER_RETRY_AT, b"not-a-timestamp")]) is None
    assert retry_due_at([]) is None
    assert retry_due_at(None) is None
