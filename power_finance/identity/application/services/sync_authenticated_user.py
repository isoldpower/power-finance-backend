from django.contrib.auth.models import User

from identity.application.dto import AuthenticatedPrincipal
from identity.infrastructure.auth.auth_sdk import AuthSdk
from identity.infrastructure.auth.clerk_sdk import ClerkSDK
from identity.infrastructure.repositories.django_user_repository import DjangoUserRepository

from ..interfaces import UserRepository


class SyncAuthenticatedUserService:
    user_repository: UserRepository = DjangoUserRepository()
    auth_sdk: AuthSdk

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        auth_sdk: AuthSdk | None = None,
    ):
        self.user_repository = user_repository or DjangoUserRepository()
        self.auth_sdk = auth_sdk or ClerkSDK()

    def execute(self, principal: AuthenticatedPrincipal) -> User:
        user = self.user_repository.get_or_create_by_external_id(principal.external_user_id)

        external_user = self.auth_sdk.fetch_user_info(principal.external_user_id)

        if external_user is not None:
            user.email = external_user.email_address
            user.first_name = external_user.first_name
            user.last_name = external_user.last_name
            user.last_login = external_user.last_login

        self.user_repository.save(user)
        return user