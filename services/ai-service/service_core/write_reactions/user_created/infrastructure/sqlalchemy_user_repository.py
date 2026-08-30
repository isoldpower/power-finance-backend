from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from service_core.shared.db_connection import UserModel

from ..repositories import UserRepository


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def remember(self, user_id: int, external_id: str, now: datetime) -> None:
        await self._session.execute(
            insert(UserModel)
            .values(user_id=user_id, external_id=external_id, created_at=now)
            .on_conflict_do_update(
                index_elements=[UserModel.user_id],
                set_={"external_id": external_id, "updated_at": now},
                where=UserModel.external_id != external_id,
            )
        )
