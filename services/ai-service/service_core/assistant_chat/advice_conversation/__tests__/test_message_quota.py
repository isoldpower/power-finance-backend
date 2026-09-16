from ..application import ConversationHandler
from ..config import QUOTA_EXHAUSTED
from ..domain.entities import AssistantQuota, MessageStatus
from .fakes import (
    CONTEXT,
    FailingGenerator,
    InMemoryMessageRepository,
    InMemoryQuotaRepository,
    ScriptedGenerator,
    StaticReferenceExtractor,
)


def _handler(quotas, generator=None) -> ConversationHandler:
    return ConversationHandler(
        messages=InMemoryMessageRepository(),
        generator=generator or ScriptedGenerator("some", " advice"),
        references=StaticReferenceExtractor(),
        quotas=quotas,
    )


async def _frames(handler, prompt: str = "How should I rearrange my assets?") -> list[dict]:
    return [frame async for frame in handler.handle({"text": prompt}, CONTEXT)]


def test_an_unused_allowance_is_fully_remaining():
    quota = AssistantQuota(allowance=10, consumed=0)

    assert quota.remaining == 10
    assert not quota.is_exhausted


def test_a_spent_allowance_is_exhausted():
    assert AssistantQuota(allowance=10, consumed=10).is_exhausted


def test_remaining_never_goes_negative():
    assert AssistantQuota(allowance=10, consumed=12).remaining == 0


async def test_a_message_spends_one_of_the_allowance():
    quotas = InMemoryQuotaRepository(allowance=10)

    await _frames(_handler(quotas))

    assert quotas.consumed == 1


async def test_the_reply_is_refused_once_the_allowance_is_gone():
    quotas = InMemoryQuotaRepository(allowance=3, consumed=3)

    frames = await _frames(_handler(quotas))

    assert [frame["event"] for frame in frames] == ["error"]
    assert frames[0]["data"]["code"] == QUOTA_EXHAUSTED


async def test_a_refused_message_stores_no_half_exchange():
    quotas = InMemoryQuotaRepository(allowance=1, consumed=1)
    store = InMemoryMessageRepository()
    handler = ConversationHandler(
        messages=store,
        generator=ScriptedGenerator("ignored"),
        references=StaticReferenceExtractor(),
        quotas=quotas,
    )

    [frame async for frame in handler.handle({"text": "hello"}, CONTEXT)]

    assert store.messages == {}


async def test_a_refusal_carries_no_message_id():
    frames = await _frames(_handler(InMemoryQuotaRepository(allowance=0)))

    assert frames[0]["data"]["message_id"] is None


async def test_a_failed_generation_gives_the_message_back():
    quotas = InMemoryQuotaRepository(allowance=10)

    await _frames(_handler(quotas, generator=FailingGenerator()))

    assert quotas.refunds == 1
    assert quotas.consumed == 0


async def test_the_allowance_runs_out_after_exactly_that_many_messages():
    quotas = InMemoryQuotaRepository(allowance=2)
    handler = _handler(quotas)

    first = await _frames(handler)
    second = await _frames(handler)
    third = await _frames(handler)

    assert first[0]["event"] == "accepted"
    assert second[0]["event"] == "accepted"
    assert third[0]["event"] == "error"


async def test_a_failed_reply_is_still_stored_as_failed():
    store = InMemoryMessageRepository()
    handler = ConversationHandler(
        messages=store,
        generator=FailingGenerator(),
        references=StaticReferenceExtractor(),
        quotas=InMemoryQuotaRepository(allowance=10),
    )

    [frame async for frame in handler.handle({"text": "hello"}, CONTEXT)]

    assert str(MessageStatus.FAILED) in {
        message.status for message in store.messages[CONTEXT.external_id]
    }


async def test_the_accepted_frame_reports_what_is_left():
    frames = await _frames(_handler(InMemoryQuotaRepository(allowance=10)))

    assert frames[0]["event"] == "accepted"
    assert frames[0]["quota"] == {"messages_left": 9, "allowance": 10}


async def test_the_settled_message_frame_reports_what_is_left():
    frames = await _frames(_handler(InMemoryQuotaRepository(allowance=4)))

    assert frames[-1]["event"] == "message"
    assert frames[-1]["quota"] == {"messages_left": 3, "allowance": 4}


async def test_the_settled_message_itself_is_unchanged_beside_the_quota():
    frames = await _frames(_handler(InMemoryQuotaRepository(allowance=4)))

    assert set(frames[-1]["data"]) == {"id", "created_at", "role", "status", "text", "refs"}


async def test_deltas_carry_no_quota():
    frames = await _frames(_handler(InMemoryQuotaRepository(allowance=4)))
    deltas = [frame for frame in frames if frame["event"] == "delta"]

    assert deltas
    assert all("quota" not in frame for frame in deltas)


async def test_a_refusal_reports_nothing_left():
    frames = await _frames(_handler(InMemoryQuotaRepository(allowance=3, consumed=3)))

    assert frames[0]["quota"] == {"messages_left": 0, "allowance": 3}


async def test_a_failed_generation_reports_the_message_given_back():
    quotas = InMemoryQuotaRepository(allowance=6)

    frames = await _frames(_handler(quotas, generator=FailingGenerator()))

    assert frames[0]["quota"] == {"messages_left": 5, "allowance": 6}
    assert frames[-1]["event"] == "error"
    assert frames[-1]["quota"] == {"messages_left": 6, "allowance": 6}


async def test_what_is_left_falls_with_each_message():
    handler = _handler(InMemoryQuotaRepository(allowance=3))

    left = [(await _frames(handler))[0]["quota"]["messages_left"] for _ in range(3)]

    assert left == [2, 1, 0]
