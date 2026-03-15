from django.contrib.auth.models import User

from identity.application.interfaces import UserRepository


class DjangoUserRepository(UserRepository):
    def get_or_create_by_external_id(self, external_user_id: str) -> User:
        user, _ = User.objects.get_or_create(username=external_user_id)
        return user

    def save(self, user: User) -> None:
        user.save()