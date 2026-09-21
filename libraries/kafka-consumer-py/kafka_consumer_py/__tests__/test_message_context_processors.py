"""Context binding and sandbox filtering decorators around a message processor."""

from contextlib import suppress

from kafka_consumer_py import (
    ContextBoundMessageProcessor,
    NullMessageContextBinder,
    PermissiveSandboxTrafficPolicy,
    SandboxFilteredMessageProcessor,
    resolve_sandbox_scoped_group_id,
)
from kafka_consumer_py.fakes import make_consumed_message

SANDBOX_HEADER_NAME = "baggage"


class _RecordingProcessor:
    def __init__(self):
        self.processed = []

    async def __call__(self, message):
        self.processed.append(message)


class _RecordingBinder:
    def __init__(self, sandbox_id=None):
        self._sandbox_id = sandbox_id
        self.bind_calls = 0
        self.unbind_calls = 0

    def bind(self, headers):
        self.bind_calls += 1
        return object()

    def unbind(self, attachment_token):
        self.unbind_calls += 1

    def read_sandbox_id(self, headers):
        return self._sandbox_id


class _BaselineTrafficPolicy:
    own_sandbox_id = None

    async def is_owned_traffic(self, message_sandbox_id):
        return message_sandbox_id is None


class _SandboxTrafficPolicy:
    own_sandbox_id = "nikita"

    async def is_owned_traffic(self, message_sandbox_id):
        return message_sandbox_id == self.own_sandbox_id


async def test_context_bound_processor_binds_and_unbinds_around_inner_call():
    inner_processor = _RecordingProcessor()
    binder = _RecordingBinder()
    processor = ContextBoundMessageProcessor(inner_processor, binder)

    await processor(make_consumed_message())

    assert binder.bind_calls == 1
    assert binder.unbind_calls == 1
    assert len(inner_processor.processed) == 1


async def test_context_bound_processor_unbinds_even_when_inner_raises():
    binder = _RecordingBinder()

    async def failing_processor(message):
        raise RuntimeError("handler exploded")

    processor = ContextBoundMessageProcessor(failing_processor, binder)

    with suppress(RuntimeError):
        await processor(make_consumed_message())

    assert binder.unbind_calls == 1


async def test_baseline_consumer_processes_untagged_message():
    inner_processor = _RecordingProcessor()
    processor = SandboxFilteredMessageProcessor(
        inner_processor,
        _RecordingBinder(sandbox_id=None),
        _BaselineTrafficPolicy(),
    )

    await processor(make_consumed_message())

    assert len(inner_processor.processed) == 1


async def test_baseline_consumer_skips_sandbox_tagged_message():
    inner_processor = _RecordingProcessor()
    processor = SandboxFilteredMessageProcessor(
        inner_processor,
        _RecordingBinder(sandbox_id="nikita"),
        _BaselineTrafficPolicy(),
    )

    await processor(make_consumed_message())

    assert inner_processor.processed == []


async def test_sandbox_consumer_processes_only_its_own_message():
    own_inner_processor = _RecordingProcessor()
    own_processor = SandboxFilteredMessageProcessor(
        own_inner_processor,
        _RecordingBinder(sandbox_id="nikita"),
        _SandboxTrafficPolicy(),
    )
    foreign_inner_processor = _RecordingProcessor()
    foreign_processor = SandboxFilteredMessageProcessor(
        foreign_inner_processor,
        _RecordingBinder(sandbox_id="someone-else"),
        _SandboxTrafficPolicy(),
    )

    await own_processor(make_consumed_message())
    await foreign_processor(make_consumed_message())

    assert len(own_inner_processor.processed) == 1
    assert foreign_inner_processor.processed == []


async def test_sandbox_consumer_skips_baseline_message():
    inner_processor = _RecordingProcessor()
    processor = SandboxFilteredMessageProcessor(
        inner_processor,
        _RecordingBinder(sandbox_id=None),
        _SandboxTrafficPolicy(),
    )

    await processor(make_consumed_message())

    assert inner_processor.processed == []


async def test_null_binder_and_permissive_policy_keep_library_defaults_open():
    inner_processor = _RecordingProcessor()
    binder = NullMessageContextBinder()
    processor = ContextBoundMessageProcessor(
        SandboxFilteredMessageProcessor(
            inner_processor,
            binder,
            PermissiveSandboxTrafficPolicy(),
        ),
        binder,
    )

    await processor(make_consumed_message())

    assert len(inner_processor.processed) == 1


def test_group_id_is_suffixed_only_for_a_sandbox():
    assert resolve_sandbox_scoped_group_id("read-write-consumer", None) == "read-write-consumer"
    assert resolve_sandbox_scoped_group_id("read-write-consumer", "") == "read-write-consumer"
    assert (
        resolve_sandbox_scoped_group_id("read-write-consumer", "nikita")
        == "read-write-consumer-sbx-nikita"
    )
