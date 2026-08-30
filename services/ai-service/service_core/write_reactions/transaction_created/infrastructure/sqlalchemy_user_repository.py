from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from service_core.shared.db_connection import UserModel

from ..repositories import UserRepository


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def external_id_for(self, user_id: int) -> str | None:
        return await self._session.scalar(
            select(UserModel.external_id).where(UserModel.user_id == user_id)
        )
