from django.contrib.auth.models import User

from environment.application.interfaces import UserRepository
from environment.domain.entities import UserEntity

from ..mappers import UserMapper


class DjangoUserRepository(UserRepository):
    async def get_or_create_by_external_id(self, external_user_id: str) -> UserEntity:
        user, _ = await User.objects.aget_or_create(username=external_user_id)
        return UserMapper.to_domain(user)

    async def update_user_info(self, user: UserEntity) -> UserEntity:
        updated_user: User = await User.objects.aget(username=user.id)
        modified_fields = UserMapper.get_changed_fields(updated_user, user)

        if modified_fields:
            UserMapper.update_model(updated_user, user)
            await updated_user.asave(update_fields=modified_fields)

        return UserMapper.to_domain(updated_user)

    async def get_user_raw(self, user: UserEntity) -> User:
        return await User.objects.aget(username=user.id)
