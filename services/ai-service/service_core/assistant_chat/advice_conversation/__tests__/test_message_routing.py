"""Which handler answers, and when the search stops."""

from ..contracts import ConnectionContext
from ..handlers import TempMessageHandler
from ..message_router import MessageRouter
from .fakes import CONTEXT, RecordingHandler


class _SilentLogger:
    def info(self, *args, **kwargs) -> None: ...


async def test_the_first_responsible_handler_answers():
    passing = RecordingHandler(claims=False, name="passing")
    claiming = RecordingHandler(claims=True, reply="mine", name="claiming")

    routed = await MessageRouter([passing, claiming]).route({"a": 1}, CONTEXT)

    assert routed.claimed is True
    assert routed.replies == ("mine",)
    assert claiming.seen == [{"a": 1}]


async def test_a_singleton_handler_stops_the_dispatch():
    first = RecordingHandler(reply="first", singleton=True, name="first")
    second = RecordingHandler(reply="second", name="second")

    routed = await MessageRouter([first, second]).route({"a": 1}, CONTEXT)

    assert routed.replies == ("first",)
    assert second.seen == []


async def test_a_non_singleton_handler_lets_the_next_one_see_it():
    first = RecordingHandler(reply="first", singleton=False, name="first")
    second = RecordingHandler(reply="second", name="second")

    routed = await MessageRouter([first, second]).route({"a": 1}, CONTEXT)

    assert routed.replies == ("first", "second")


async def test_a_message_nobody_claims_is_reported_unclaimed():
    routed = await MessageRouter([RecordingHandler(claims=False)]).route({"a": 1}, CONTEXT)

    assert routed.claimed is False
    assert routed.replies == ()


async def test_a_claimed_but_silent_message_is_not_unclaimed():
    """The distinction the session acts on: silence is a normal turn, an
    unclaimed message ends the conversation."""

    routed = await MessageRouter([RecordingHandler(reply=None)]).route({"a": 1}, CONTEXT)

    assert routed.claimed is True
    assert routed.replies == ()


async def test_an_unresponsible_handler_is_never_asked_to_handle():
    declining = RecordingHandler(claims=False)

    await MessageRouter([declining]).route({"a": 1}, CONTEXT)

    assert declining.judged == [{"a": 1}]
    assert declining.seen == []


async def test_the_scaffolding_handler_claims_only_what_it_can_greet():
    handler = TempMessageHandler(_SilentLogger())
    context = ConnectionContext(path="/chat", external_id="clerk_7")

    assert await handler.is_responsible({"name": "Nikita"}, context) is True
    assert await handler.is_responsible({"message": "hi"}, context) is False
    assert await handler.is_responsible({"name": 7}, context) is False


async def test_the_scaffolding_handler_greets_without_reading_the_socket():
    """It judges a value it was handed. Reading a frame to decide would consume
    the one the next handler has to judge, and the one it meant to answer."""

    handler = TempMessageHandler(_SilentLogger())
    context = ConnectionContext(path="/chat", external_id="clerk_7")

    assert await handler.handle({"name": "Nikita"}, context) == "Hello, Nikita"
