from django.contrib.auth import get_user_model

from data_write_core.application.interfaces import UserRepository
from data_write_core.domain.entities import InternalUserEntity

from .mappers import UserMapper


class DjangoUserRepository(UserRepository):
    def __init__(self):
        self._UserModel = get_user_model()

    async def get_synced_internal(self, external_id: str) -> InternalUserEntity:
        internal_user, _ = await self._UserModel.objects.aget_or_create(username=external_id)

        return UserMapper.to_domain(internal_user)
