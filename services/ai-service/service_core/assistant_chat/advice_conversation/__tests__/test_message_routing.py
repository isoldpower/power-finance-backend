"""Which handler answers, and when the search stops."""

from ..message_router import MessageRouter
from .fakes import CONTEXT, RecordingHandler


async def _frames(routed) -> list[dict]:
    return [frame async for frame in routed.frames]


async def test_the_first_responsible_handler_answers():
    passing = RecordingHandler(claims=False, name="passing")
    claiming = RecordingHandler(claims=True, reply="mine", name="claiming")

    routed = await MessageRouter([passing, claiming]).route({"a": 1}, CONTEXT)

    assert routed.claimed is True
    assert await _frames(routed) == [{"reply": "mine"}]
    assert claiming.seen == [{"a": 1}]


async def test_a_singleton_handler_stops_the_dispatch():
    first = RecordingHandler(reply="first", singleton=True, name="first")
    second = RecordingHandler(reply="second", name="second")

    routed = await MessageRouter([first, second]).route({"a": 1}, CONTEXT)

    assert await _frames(routed) == [{"reply": "first"}]
    assert second.seen == []


async def test_a_non_singleton_handler_lets_the_next_one_see_it():
    first = RecordingHandler(reply="first", singleton=False, name="first")
    second = RecordingHandler(reply="second", name="second")

    routed = await MessageRouter([first, second]).route({"a": 1}, CONTEXT)

    assert await _frames(routed) == [{"reply": "first"}, {"reply": "second"}]


async def test_a_message_nobody_claims_is_reported_unclaimed():
    routed = await MessageRouter([RecordingHandler(claims=False)]).route({"a": 1}, CONTEXT)

    assert routed.claimed is False
    assert await _frames(routed) == []


async def test_a_claimed_but_silent_message_is_not_unclaimed():
    """The distinction the session acts on: silence is a normal turn, an
    unclaimed message ends the conversation."""

    routed = await MessageRouter([RecordingHandler(reply=None)]).route({"a": 1}, CONTEXT)

    assert routed.claimed is True
    assert await _frames(routed) == []


async def test_an_unresponsible_handler_is_never_asked_to_handle():
    declining = RecordingHandler(claims=False)

    routed = await MessageRouter([declining]).route({"a": 1}, CONTEXT)
    await _frames(routed)

    assert declining.judged == [{"a": 1}]
    assert declining.seen == []


async def test_claiming_is_settled_before_anything_is_generated():
    """`claimed` is the routing decision, and the session refuses an unroutable
    frame on it. Reading it must not have started a handler."""

    handler = RecordingHandler()

    routed = await MessageRouter([handler]).route({"a": 1}, CONTEXT)

    assert routed.claimed is True
    assert handler.seen == []
