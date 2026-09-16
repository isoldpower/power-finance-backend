from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from service_core.shared.db_connection import AssistantQuotaModel

from ...application.contracts import QuotaRepository
from ...application.dtos import QuotaDecisionDTO
from ...config import DEFAULT_MESSAGE_ALLOWANCE


class SqlAlchemyQuotaRepository(QuotaRepository):
    def __init__(
        self,
        session_factory: async_sessionmaker,
        default_allowance: int = DEFAULT_MESSAGE_ALLOWANCE,
    ) -> None:
        self._session_factory = session_factory
        self._default_allowance = default_allowance

    # One statement, so two sockets opened by the same user cannot both read a
    # spare message and both spend it. The guard rides on the conflict branch: an
    # exhausted row matches nothing, updates nothing, and returns nothing.
    async def consume_message(self, external_id: str) -> QuotaDecisionDTO:
        now = datetime.now(UTC)
        statement = (
            insert(AssistantQuotaModel)
            .values(
                external_id=external_id,
                message_allowance=self._default_allowance,
                messages_consumed=1,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=[AssistantQuotaModel.external_id],
                set_={
                    "messages_consumed": AssistantQuotaModel.messages_consumed + 1,
                    "updated_at": now,
                },
                where=AssistantQuotaModel.messages_consumed < AssistantQuotaModel.message_allowance,
            )
            .returning(
                AssistantQuotaModel.message_allowance,
                AssistantQuotaModel.messages_consumed,
            )
        )

        async with self._session_factory() as session, session.begin():
            granted = (await session.execute(statement)).one_or_none()

        if granted is not None:
            return QuotaDecisionDTO(
                granted=True,
                allowance=granted.message_allowance,
                consumed=granted.messages_consumed,
            )

        return await self._refusal(external_id)

    async def refund_message(self, external_id: str) -> QuotaDecisionDTO:
        statement = (
            update(AssistantQuotaModel)
            .where(
                AssistantQuotaModel.external_id == external_id,
                AssistantQuotaModel.messages_consumed > 0,
            )
            .values(
                messages_consumed=AssistantQuotaModel.messages_consumed - 1,
                updated_at=datetime.now(UTC),
            )
            .returning(
                AssistantQuotaModel.message_allowance,
                AssistantQuotaModel.messages_consumed,
            )
        )

        async with self._session_factory() as session, session.begin():
            refunded = (await session.execute(statement)).one_or_none()

        if refunded is None:
            return await self._current(external_id)

        return QuotaDecisionDTO(
            granted=True,
            allowance=refunded.message_allowance,
            consumed=refunded.messages_consumed,
        )

    async def _refusal(self, external_id: str) -> QuotaDecisionDTO:
        current = await self._current(external_id)

        return current._replace(granted=False)

    async def _current(self, external_id: str) -> QuotaDecisionDTO:
        async with self._session_factory() as session:
            stored = await session.get(AssistantQuotaModel, external_id)

        if stored is None:
            return QuotaDecisionDTO(
                granted=False,
                allowance=self._default_allowance,
                consumed=0,
            )

        return QuotaDecisionDTO(
            granted=False,
            allowance=stored.message_allowance,
            consumed=stored.messages_consumed,
        )
