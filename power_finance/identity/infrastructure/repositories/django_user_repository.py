from django.contrib.auth.models import User

from identity.application.interfaces import UserRepository
from identity.domain.entities import UserEntity

from ..mappers import UserMapper


class DjangoUserRepository(UserRepository):
    def get_or_create_by_external_id(self, external_user_id: str) -> UserEntity:
        user, _ = User.objects.get_or_create(username=external_user_id)

        return UserMapper.to_domain(user)

    def update_user_info(self, user: UserEntity) -> UserEntity:
        updated_user: User = User.objects.get(username=user.id)
        modified_fields = UserMapper.get_changed_fields(updated_user, user)

        UserMapper.update_model(updated_user, user)

        updated_user.save(update_fields=modified_fields)
        return UserMapper.to_domain(updated_user)

    def get_user_raw(self, user: UserEntity) -> User:
        return User.objects.get(username=user.id)
