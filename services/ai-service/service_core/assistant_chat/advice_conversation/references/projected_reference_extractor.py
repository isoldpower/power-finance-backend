import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from service_core.shared.db_connection import (
    AccountModel,
    ProjectedTransaction,
    UserModel,
)

from ..contracts import (
    ConnectionContext,
    ReferenceExtractor,
    ResourceReference,
)

TRANSACTION = "transaction"
ACCOUNT = "account"
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)


class ProjectedReferenceExtractor(ReferenceExtractor):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def extract(
        self,
        text: str,
        context: ConnectionContext,
    ) -> tuple[ResourceReference, ...]:
        mentioned = _mentioned_ids(text)
        if not mentioned:
            return ()

        async with self._session_factory() as session:
            user_id = await session.scalar(
                select(UserModel.user_id).where(UserModel.external_id == context.external_id)
            )
            if user_id is None:
                return ()

            owned = await self._owned_ids(session, user_id, mentioned)

        return tuple(
            ResourceReference(type=owned[candidate], id=candidate)
            for candidate in mentioned
            if candidate in owned
        )

    async def _owned_ids(
        self,
        session,
        user_id: int,
        candidates: list[UUID],
    ) -> dict[UUID, str]:
        transactions = await session.scalars(
            select(ProjectedTransaction.id).where(
                ProjectedTransaction.user_id == user_id,
                ProjectedTransaction.id.in_(candidates),
                ProjectedTransaction.deleted_at.is_(None),
            )
        )
        accounts = await session.scalars(
            select(AccountModel.id).where(
                AccountModel.user_id == user_id,
                AccountModel.id.in_(candidates),
            )
        )

        resolved: dict[UUID, str] = {found: TRANSACTION for found in transactions}
        resolved.update({found: ACCOUNT for found in accounts})

        return resolved


def _mentioned_ids(text: str) -> list[UUID]:
    seen: dict[UUID, None] = {}
    for match in UUID_PATTERN.findall(text):
        seen.setdefault(UUID(match), None)

    return list(seen)
