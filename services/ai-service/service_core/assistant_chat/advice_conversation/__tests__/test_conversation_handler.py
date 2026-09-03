"""One turn of the conversation: what is persisted, in what order, and what
survives a generation that fails."""

from uuid import UUID, uuid4

from ..contracts import MessageRole, MessageStatus, ResourceReference
from ..handlers import ConversationHandler
from .fakes import (
    CONTEXT,
    ExplodingReferenceExtractor,
    FailingGenerator,
    InMemoryMessageRepository,
    ScriptedGenerator,
    StaticReferenceExtractor,
)

TRANSACTION_ID = UUID("b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92")


def _handler(store, generator, references=None) -> ConversationHandler:
    return ConversationHandler(
        messages=store,
        generator=generator,
        references=references or StaticReferenceExtractor(),
    )


async def _frames(handler, prompt: str = "Why is my dining spend up?") -> list[dict]:
    return [frame async for frame in handler.handle({"text": prompt}, CONTEXT)]


async def test_only_a_frame_carrying_text_is_claimed():
    handler = _handler(InMemoryMessageRepository(), ScriptedGenerator("hi"))

    assert await handler.is_responsible({"text": "hello"}, CONTEXT) is True
    assert await handler.is_responsible({"name": "Nikita"}, CONTEXT) is False
    assert await handler.is_responsible({"text": 7}, CONTEXT) is False


async def test_the_turn_is_accepted_then_streamed_then_settled():
    handler = _handler(InMemoryMessageRepository(), ScriptedGenerator("one ", "two"))

    events = [frame["event"] for frame in await _frames(handler)]

    assert events == ["accepted", "delta", "delta", "message"]


async def test_both_messages_are_stored_before_any_text_exists():
    """`accepted` promises the ids are real. It arrives before generation, so
    a client that drops immediately can still refetch the answer."""

    store = InMemoryMessageRepository()
    handler = _handler(store, ScriptedGenerator("text"))

    frames = await _frames(handler, "a question")
    accepted = frames[0]["data"]

    question, answer = store.stored()
    assert str(question.id) == accepted["user_message_id"]
    assert str(answer.id) == accepted["message_id"]


async def test_the_question_is_stored_complete_and_uncited():
    """User messages always have `status: complete` and empty `refs`."""

    store = InMemoryMessageRepository()
    await _frames(_handler(store, ScriptedGenerator("text")), "a question")

    question = store.stored()[0]
    assert question.role is MessageRole.USER
    assert question.status is MessageStatus.COMPLETE
    assert question.text == "a question"
    assert question.refs == ()


async def test_the_answer_settles_complete_with_the_whole_text():
    store = InMemoryMessageRepository()
    handler = _handler(store, ScriptedGenerator("You spent ", "412.30 USD"))

    frames = await _frames(handler)

    answer = store.stored()[1]
    assert answer.status is MessageStatus.COMPLETE
    assert answer.text == "You spent 412.30 USD"
    assert frames[-1]["data"]["text"] == answer.text


async def test_references_are_attached_once_the_text_is_whole():
    """They are not knowable until generation completes, which is why the
    terminal frame repeats the full text rather than only announcing the end."""

    store = InMemoryMessageRepository()
    references = StaticReferenceExtractor(ResourceReference(type="transaction", id=TRANSACTION_ID))
    handler = _handler(store, ScriptedGenerator("a ", "reply"), references)

    frames = await _frames(handler)

    assert references.texts == ["a reply"]
    assert frames[-1]["data"]["refs"] == [{"type": "transaction", "id": str(TRANSACTION_ID)}]
    assert store.stored()[1].refs == (ResourceReference(type="transaction", id=TRANSACTION_ID),)


async def test_deltas_carry_text_only():
    handler = _handler(InMemoryMessageRepository(), ScriptedGenerator("one ", "two"))

    deltas = [frame for frame in await _frames(handler) if frame["event"] == "delta"]

    assert [frame["data"] for frame in deltas] == [{"text": "one "}, {"text": "two"}]


async def test_a_failed_generation_keeps_what_it_produced():
    """A user who watched half an answer appear and then vanish has no way to
    tell that from a bug, so the partial reply is stored rather than dropped."""

    store = InMemoryMessageRepository()
    handler = _handler(store, FailingGenerator("You spent "))

    frames = await _frames(handler)

    assert frames[-1]["event"] == "error"
    answer = store.stored()[1]
    assert answer.status is MessageStatus.FAILED
    assert answer.text == "You spent "


async def test_a_failed_generation_names_the_message_it_abandoned():
    store = InMemoryMessageRepository()
    handler = _handler(store, FailingGenerator())

    failure = (await _frames(handler))[-1]["data"]

    assert failure["code"] == "assistant_unavailable"
    assert failure["message_id"] == str(store.stored()[1].id)


async def test_a_failure_does_not_produce_a_message_frame():
    """`error` is terminal for the turn. A client that saw both would not know
    which one to believe."""

    handler = _handler(InMemoryMessageRepository(), FailingGenerator("half"))

    events = [frame["event"] for frame in await _frames(handler)]

    assert "message" not in events


async def test_a_broken_reference_lookup_does_not_cost_the_user_their_answer():
    """The text is the reply; the chips beside it are a convenience."""

    store = InMemoryMessageRepository()
    handler = _handler(
        store,
        ScriptedGenerator("a reply"),
        ExplodingReferenceExtractor(),
    )

    frames = await _frames(handler)

    assert frames[-1]["event"] == "message"
    assert frames[-1]["data"]["refs"] == []
    assert store.stored()[1].status is MessageStatus.COMPLETE


async def test_the_prompt_reaches_the_generator_verbatim():
    generator = ScriptedGenerator("ok")
    await _frames(_handler(InMemoryMessageRepository(), generator), "  spaced  ")

    assert generator.prompts == ["  spaced  "]


async def test_each_turn_gets_its_own_pair_of_ids():
    store = InMemoryMessageRepository()
    handler = _handler(store, ScriptedGenerator("ok"))

    await _frames(handler, "first")
    await _frames(handler, "second")

    identifiers = {message.id for message in store.stored()}
    assert len(identifiers) == 4
    assert uuid4() not in identifiers
