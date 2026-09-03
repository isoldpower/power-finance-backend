"""The conversation's storage, against a real Postgres.

The parts worth testing here are the keyset page and the hard delete — exactly
the parts a fake store would have to reimplement in order to be wrong about.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from service_core.shared.db_connection import get_session_factory

from ..contracts import (
    ConversationMessage,
    MessageRole,
    MessageStatus,
    ResourceReference,
)
from ..infrastructure import SqlAlchemyMessageRepository

OWNER = "clerk_7"
STRANGER = "clerk_9"
NOON = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
TRANSACTION_ID = UUID("b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92")


def _store() -> SqlAlchemyMessageRepository:
    return SqlAlchemyMessageRepository(get_session_factory())


def _message(
    *,
    minute: int = 0,
    role: MessageRole = MessageRole.USER,
    status: MessageStatus = MessageStatus.COMPLETE,
    text: str = "hello",
    refs: tuple[ResourceReference, ...] = (),
) -> ConversationMessage:
    return ConversationMessage(
        id=uuid4(),
        role=role,
        status=status,
        text=text,
        created_at=NOON + timedelta(minutes=minute),
        refs=refs,
    )


async def _seed(store, owner: str, count: int) -> list[ConversationMessage]:
    written = [_message(minute=index, text=f"message {index}") for index in range(count)]
    for message in written:
        await store.append(owner, message)

    return written


async def test_a_stored_message_round_trips():
    store = _store()
    written = _message(
        role=MessageRole.ASSISTANT,
        text="You spent 412.30 USD",
        refs=(ResourceReference(type="transaction", id=TRANSACTION_ID),),
    )

    await store.append(OWNER, written)
    read = (await store.page(OWNER, limit=10))[0]

    assert read == written


async def test_the_feed_is_newest_first():
    store = _store()
    await _seed(store, OWNER, 3)

    page = await store.page(OWNER, limit=10)

    assert [message.text for message in page] == ["message 2", "message 1", "message 0"]


async def test_a_page_carries_the_lookahead_row():
    """`build_page` mints cursors from it, so the store has to return
    `limit + 1` rather than exactly `limit`."""

    store = _store()
    await _seed(store, OWNER, 5)

    assert len(await store.page(OWNER, limit=2)) == 3


async def test_a_forward_anchor_continues_past_it():
    store = _store()
    written = await _seed(store, OWNER, 5)
    anchor = written[3]  # "message 3", second newest

    page = await store.page(OWNER, limit=10, anchor=(anchor.created_at, anchor.id))

    assert [message.text for message in page] == ["message 2", "message 1", "message 0"]


async def test_a_backward_anchor_returns_the_newer_side_still_newest_first():
    """A backward scan walks the opposite way and is reversed before it is
    returned, so a caller only ever sees the order the feed is served in."""

    store = _store()
    written = await _seed(store, OWNER, 5)
    anchor = written[1]

    page = await store.page(
        OWNER,
        limit=10,
        anchor=(anchor.created_at, anchor.id),
        backwards=True,
    )

    assert [message.text for message in page] == ["message 4", "message 3", "message 2"]


async def test_one_users_conversation_is_not_another_users():
    store = _store()
    await _seed(store, OWNER, 2)
    await _seed(store, STRANGER, 3)

    assert len(await store.page(OWNER, limit=10)) == 2
    assert await store.count(OWNER) == 2
    assert await store.count(STRANGER) == 3


async def test_settling_closes_out_a_streaming_message():
    store = _store()
    answer = _message(role=MessageRole.ASSISTANT, status=MessageStatus.STREAMING, text="")
    await store.append(OWNER, answer)

    await store.settle(
        answer.id,
        MessageStatus.COMPLETE,
        "the whole answer",
        (ResourceReference(type="transaction", id=TRANSACTION_ID),),
    )

    settled = (await store.page(OWNER, limit=10))[0]
    assert settled.status is MessageStatus.COMPLETE
    assert settled.text == "the whole answer"
    assert settled.refs == (ResourceReference(type="transaction", id=TRANSACTION_ID),)


async def test_a_failed_message_keeps_its_partial_text():
    store = _store()
    answer = _message(role=MessageRole.ASSISTANT, status=MessageStatus.STREAMING, text="")
    await store.append(OWNER, answer)

    await store.settle(answer.id, MessageStatus.FAILED, "half an ans", ())

    failed = (await store.page(OWNER, limit=10))[0]
    assert failed.status is MessageStatus.FAILED
    assert failed.text == "half an ans"


async def test_clearing_reports_what_it_deleted():
    store = _store()
    await _seed(store, OWNER, 4)

    assert await store.clear(OWNER) == 4
    assert await store.page(OWNER, limit=10) == []


async def test_clearing_an_empty_conversation_succeeds_with_zero():
    assert await _store().clear(OWNER) == 0


async def test_clearing_leaves_other_conversations_alone():
    store = _store()
    await _seed(store, OWNER, 2)
    await _seed(store, STRANGER, 3)

    await store.clear(OWNER)

    assert await store.count(STRANGER) == 3
