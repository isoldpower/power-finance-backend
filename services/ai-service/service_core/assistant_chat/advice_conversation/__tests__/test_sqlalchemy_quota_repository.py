import asyncio

from service_core.shared.db_connection import AssistantQuotaModel, get_session_factory

from ..config import DEFAULT_MESSAGE_ALLOWANCE
from ..infrastructure import SqlAlchemyQuotaRepository

EXTERNAL_ID = "user_quota_subject"


def _repository(default_allowance: int | None = None) -> SqlAlchemyQuotaRepository:
    if default_allowance is None:
        return SqlAlchemyQuotaRepository(get_session_factory())

    return SqlAlchemyQuotaRepository(get_session_factory(), default_allowance=default_allowance)


async def _stored() -> AssistantQuotaModel | None:
    async with get_session_factory()() as session:
        return await session.get(AssistantQuotaModel, EXTERNAL_ID)


async def test_a_first_message_grants_the_default_allowance():
    decision = await _repository().consume_message(EXTERNAL_ID)

    assert decision.granted
    assert decision.allowance == DEFAULT_MESSAGE_ALLOWANCE
    assert decision.consumed == 1


async def test_the_default_allowance_is_ten():
    assert DEFAULT_MESSAGE_ALLOWANCE == 10


async def test_a_grant_is_written_once_and_then_incremented():
    repository = _repository()

    await repository.consume_message(EXTERNAL_ID)
    await repository.consume_message(EXTERNAL_ID)

    row = await _stored()
    assert row.message_allowance == DEFAULT_MESSAGE_ALLOWANCE
    assert row.messages_consumed == 2


async def test_messages_beyond_the_allowance_are_refused():
    repository = _repository(default_allowance=2)

    assert (await repository.consume_message(EXTERNAL_ID)).granted
    assert (await repository.consume_message(EXTERNAL_ID)).granted

    refused = await repository.consume_message(EXTERNAL_ID)

    assert not refused.granted
    assert refused.allowance == 2
    assert refused.consumed == 2


async def test_a_refusal_does_not_keep_counting():
    repository = _repository(default_allowance=1)

    await repository.consume_message(EXTERNAL_ID)
    await repository.consume_message(EXTERNAL_ID)
    await repository.consume_message(EXTERNAL_ID)

    assert (await _stored()).messages_consumed == 1


async def test_an_allowance_raised_by_hand_is_honoured():
    repository = _repository(default_allowance=1)
    await repository.consume_message(EXTERNAL_ID)
    assert not (await repository.consume_message(EXTERNAL_ID)).granted

    async with get_session_factory()() as session, session.begin():
        row = await session.get(AssistantQuotaModel, EXTERNAL_ID)
        row.message_allowance = 5

    assert (await repository.consume_message(EXTERNAL_ID)).granted


async def test_a_refund_returns_one_message():
    repository = _repository(default_allowance=1)
    await repository.consume_message(EXTERNAL_ID)

    await repository.refund_message(EXTERNAL_ID)

    assert (await _stored()).messages_consumed == 0
    assert (await repository.consume_message(EXTERNAL_ID)).granted


async def test_a_refund_cannot_push_the_count_below_zero():
    repository = _repository()
    await repository.consume_message(EXTERNAL_ID)

    await repository.refund_message(EXTERNAL_ID)
    await repository.refund_message(EXTERNAL_ID)

    assert (await _stored()).messages_consumed == 0


async def test_concurrent_messages_cannot_overspend_the_allowance():
    repository = _repository(default_allowance=3)

    decisions = await asyncio.gather(*(repository.consume_message(EXTERNAL_ID) for _ in range(10)))

    assert sum(decision.granted for decision in decisions) == 3
    assert (await _stored()).messages_consumed == 3


async def test_quotas_are_held_per_user():
    repository = _repository(default_allowance=1)

    await repository.consume_message(EXTERNAL_ID)
    other = await repository.consume_message("user_someone_else")

    assert other.granted


async def test_a_refund_reports_the_restored_balance():
    repository = _repository(default_allowance=5)
    await repository.consume_message(EXTERNAL_ID)

    refunded = await repository.refund_message(EXTERNAL_ID)

    assert refunded.allowance == 5
    assert refunded.consumed == 0


async def test_refunding_a_user_who_never_spent_reports_the_default_allowance():
    refunded = await _repository(default_allowance=7).refund_message(EXTERNAL_ID)

    assert refunded.allowance == 7
    assert refunded.consumed == 0


async def test_a_refusal_reports_the_allowance_it_was_measured_against():
    repository = _repository(default_allowance=2)
    await repository.consume_message(EXTERNAL_ID)
    await repository.consume_message(EXTERNAL_ID)

    refused = await repository.consume_message(EXTERNAL_ID)

    assert (refused.allowance, refused.consumed) == (2, 2)
