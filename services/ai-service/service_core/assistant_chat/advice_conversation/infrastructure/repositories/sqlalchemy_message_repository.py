from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from service_core.shared.db_connection import AssistantMessageModel

from ...application.contracts import MessageRepository
from ...application.dtos import ConversationMessageDTO, ResourceReferenceDTO
from .mappers import AssistantMessageMapper


class SqlAlchemyMessageRepository(MessageRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def append(self, external_id: str, message: ConversationMessageDTO) -> None:
        async with self._session_factory() as session, session.begin():
            session.add(AssistantMessageMapper.to_model(external_id, message))

    async def settle(
        self,
        message_id: UUID,
        status: str,
        text: str,
        refs: tuple[ResourceReferenceDTO, ...],
    ) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                update(AssistantMessageModel)
                .where(AssistantMessageModel.id == message_id)
                .values(
                    status=status,
                    text=text,
                    refs=AssistantMessageMapper.refs_to_columns(refs),
                )
            )

    async def page(
        self,
        external_id: str,
        limit: int,
        anchor: tuple | None = None,
        backwards: bool = False,
    ) -> list[ConversationMessageDTO]:
        statement = select(AssistantMessageModel).where(
            AssistantMessageModel.external_id == external_id
        )

        if anchor is None:
            statement = statement.order_by(
                AssistantMessageModel.created_at.desc(),
                AssistantMessageModel.id.desc(),
            )
        elif backwards:
            statement = statement.where(_keyset(anchor, ascending=True)).order_by(
                AssistantMessageModel.created_at.asc(),
                AssistantMessageModel.id.asc(),
            )
        else:
            statement = statement.where(_keyset(anchor, ascending=False)).order_by(
                AssistantMessageModel.created_at.desc(),
                AssistantMessageModel.id.desc(),
            )

        async with self._session_factory() as session:
            rows = list(await session.scalars(statement.limit(limit + 1)))

        if backwards:
            rows.reverse()

        return [AssistantMessageMapper.to_dto(row) for row in rows]

    async def count(self, external_id: str) -> int:
        async with self._session_factory() as session:
            total = await session.scalar(
                select(func.count())
                .select_from(AssistantMessageModel)
                .where(AssistantMessageModel.external_id == external_id)
            )

        return int(total or 0)

    async def clear(self, external_id: str) -> int:
        async with self._session_factory() as session, session.begin():
            result = await session.execute(
                delete(AssistantMessageModel).where(
                    AssistantMessageModel.external_id == external_id
                )
            )

        return int(result.rowcount or 0)


def _keyset(anchor: tuple, ascending: bool):
    created_at, message_id = anchor
    columns = (AssistantMessageModel.created_at, AssistantMessageModel.id)

    return (
        tuple(columns) > (created_at, message_id)
        if ascending
        else tuple(columns) < (created_at, message_id)
    )
