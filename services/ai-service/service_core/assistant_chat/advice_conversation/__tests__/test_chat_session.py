import asyncio

from ..application import (
    ChatSession,
    MessageRouter,
    NeverTerminates,
    ProcessShutdownSignal,
)
from ..application.contracts import ConnectionContext, Termination, TerminationReason
from .fakes import (
    CONTEXT,
    ClientDisconnectedError,
    DisconnectingTransport,
    ExplodingHandler,
    ImmediateSignal,
    MalformedFrameError,
    RecordingHandler,
    ScriptedTransport,
)

RUN_TIMEOUT_SECONDS = 2


def _session(transport, handlers=None, signal=None, context: ConnectionContext = CONTEXT):
    return ChatSession(
        transport=transport,
        router=MessageRouter(handlers if handlers is not None else [RecordingHandler()]),
        termination_signal=signal or NeverTerminates(),
        context=context,
    )


async def _run(session) -> Termination:
    return await asyncio.wait_for(session.run(), timeout=RUN_TIMEOUT_SECONDS)


async def test_a_claimed_message_is_answered():
    transport = ScriptedTransport([{"say": "hi"}, ClientDisconnectedError])

    await _run(_session(transport))

    assert transport.sent == [{"reply": "answered"}]


async def test_the_conversation_continues_across_turns():
    handler = RecordingHandler()
    transport = ScriptedTransport([{"n": 1}, {"n": 2}, {"n": 3}, ClientDisconnectedError])

    await _run(_session(transport, [handler]))

    assert handler.seen == [{"n": 1}, {"n": 2}, {"n": 3}]
    assert transport.sent == [{"reply": "answered"}] * 3


async def test_a_handler_may_claim_a_message_and_answer_with_silence():
    handler = RecordingHandler(reply=None)
    transport = ScriptedTransport([{"say": "hi"}, ClientDisconnectedError])

    await _run(_session(transport, [handler]))

    assert handler.seen == [{"say": "hi"}]
    assert transport.sent == []


async def test_a_client_that_hangs_up_ends_the_conversation_unannounced():
    transport = ScriptedTransport([ClientDisconnectedError])

    termination = await _run(_session(transport))

    assert termination == Termination.client_disconnected()
    assert termination.code == TerminationReason.NORMAL_CLOSURE
    assert transport.closed_with is None


async def test_a_client_that_hangs_up_mid_reply_ends_the_conversation():
    transport = DisconnectingTransport([{"say": "hi"}])

    termination = await _run(_session(transport))

    assert termination.reason == "client_disconnected"


async def test_a_frame_that_is_not_json_ends_the_conversation():
    transport = ScriptedTransport([MalformedFrameError])

    termination = await _run(_session(transport))

    assert termination.reason == "malformed_message"
    assert transport.closed_with is not None
    assert transport.closed_with.code == TerminationReason.UNSUPPORTED_DATA


async def test_a_message_no_handler_claims_ends_the_conversation():
    transport = ScriptedTransport([{"unknown": True}])

    termination = await _run(_session(transport, [RecordingHandler(claims=False)]))

    assert termination.reason == "unroutable_message"
    assert transport.closed_with.code == TerminationReason.UNSUPPORTED_DATA


async def test_a_signal_that_has_already_fired_stops_before_the_first_turn():
    handler = RecordingHandler()
    transport = ScriptedTransport([{"say": "hi"}])

    termination = await _run(_session(transport, [handler], ImmediateSignal()))

    assert termination.reason == "server_shutting_down"
    assert handler.seen == []
    assert transport.closed_with.code == TerminationReason.GOING_AWAY


async def test_a_signal_that_fires_mid_conversation_closes_the_socket():
    signal = ProcessShutdownSignal()
    transport = ScriptedTransport([])
    session = _session(transport, signal=signal)

    running = asyncio.ensure_future(session.run())
    await asyncio.sleep(0)
    signal.terminate(Termination.server_shutting_down())

    termination = await asyncio.wait_for(running, timeout=2)

    assert termination.reason == "server_shutting_down"
    assert transport.closed_with.code == TerminationReason.GOING_AWAY


async def test_the_loop_leaves_no_task_behind():
    before = len(asyncio.all_tasks())
    transport = ScriptedTransport([{"n": 1}, {"n": 2}, ClientDisconnectedError])

    await _run(_session(transport))

    assert len(asyncio.all_tasks()) == before


async def test_handlers_are_told_who_is_connected():
    handler = RecordingHandler()
    context = ConnectionContext(path="/api/v1/chat/advice", external_id="clerk_99")
    transport = ScriptedTransport([{"say": "hi"}, ClientDisconnectedError])

    await _run(_session(transport, [handler], context=context))

    assert [seen.external_id for seen in handler.contexts] == ["clerk_99"]
    assert [seen.path for seen in handler.contexts] == ["/api/v1/chat/advice"]


async def test_a_handler_that_raises_closes_the_socket_rather_than_hanging():
    transport = ScriptedTransport([{"say": "hi"}])

    termination = await _run(_session(transport, [ExplodingHandler()]))

    assert termination.reason == "handler_failed"
    assert transport.closed_with.code == TerminationReason.INTERNAL_ERROR


async def test_frames_are_forwarded_one_at_a_time_as_they_are_produced():
    handler = RecordingHandler(
        frames=({"event": "accepted"}, {"event": "delta"}, {"event": "message"}),
    )
    transport = ScriptedTransport([{"text": "hi"}, ClientDisconnectedError])

    await _run(_session(transport, [handler]))

    assert [frame["event"] for frame in transport.sent] == ["accepted", "delta", "message"]
