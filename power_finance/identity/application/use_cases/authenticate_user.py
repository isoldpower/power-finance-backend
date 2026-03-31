from dataclasses import dataclass
from django.conf import settings

from ..interfaces import ExternalAuth, UserRepository

from identity.infrastructure.integration import ClerkAuth
from identity.infrastructure.repositories import DjangoUserRepository
from identity.infrastructure.cache import DjangoCacheStorage
from identity.domain.services import decode_jwt_contents


@dataclass(frozen=True)
class AuthenticateUserCommand:
    auth_header: str


class AuthenticateUserCommandHandler:
    _external_auth: ExternalAuth
    _user_repository: UserRepository

    def __init__(
            self,
            user_repository: UserRepository | None = None,
            external_auth: ExternalAuth | None = None
    ):
        self._user_repository = user_repository or DjangoUserRepository()
        self._external_auth = external_auth or ClerkAuth(
            cache_storage=DjangoCacheStorage(settings.RESOLVED_ENV["CLERK_CACHE_KEY"]),
            issuer_url=settings.RESOLVED_ENV["CLERK_API_URL"],
            secret_key=settings.RESOLVED_ENV["CLERK_SECRET_KEY"],
            api_base_url="https://api.clerk.com/v1",
        )

    def handle(self, command: AuthenticateUserCommand):
        token = self._external_auth.resolve_auth_token(command.auth_header)
        if not token:
            return None

        principal = decode_jwt_contents(
            token,
            self._external_auth.get_jwks()
        )
        external_user = self._external_auth.fetch_user_info(principal.external_user_id)
        internal_user = self._user_repository.get_or_create_by_external_id(principal.external_user_id)
        internal_user.sync_with_external(external_user)

        user = self._user_repository.update_user_info(internal_user)
        user_model = self._user_repository.get_user_raw(user)

        return user_model, token