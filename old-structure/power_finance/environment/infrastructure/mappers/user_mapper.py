from django.contrib.auth.models import User

from environment.domain.entities import UserEntity

from .update_mapper import UpdateMapper


class UserMapper:
    USER_EDITABLE_MAP: list[tuple[str, str]] = [
        ('email', 'email'),
        ('first_name', 'first_name'),
        ('last_name', 'last_name'),
        ('last_login', 'last_login'),
    ]

    @staticmethod
    def to_domain(user: User):
        return UserEntity.from_persistence(
            id=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            last_login=user.last_login,
        )

    @staticmethod
    def update_model(model: User, entity: UserEntity) -> User:
        return UpdateMapper[User, UserEntity].update_model(
            model,
            entity,
            UserMapper.USER_EDITABLE_MAP,
        )

    @staticmethod
    def get_changed_fields(model: User, entity: UserEntity) -> list[str]:
        return UpdateMapper[User, UserEntity].get_changed_fields(
            model,
            entity,
            UserMapper.USER_EDITABLE_MAP,
        )