import hashlib
from dataclasses import dataclass
from django.conf import settings
from django.contrib.auth.models import User

from ..interfaces import ExternalAuth, UserRepository, CacheStorage

from environment.domain.services import decode_jwt_contents
from environment.domain.entities import UserEntity
from environment.infrastructure.integration import ClerkAuth
from environment.infrastructure.repositories import DjangoUserRepository
from environment.infrastructure.cache import DjangoCacheStorage


@dataclass(frozen=True)
class AuthenticateUserCommand:
    auth_header: str


class AuthenticateUserCommandHandler:
    _external_auth: ExternalAuth
    _user_repository: UserRepository
    _cache_storage: CacheStorage
    _jwks_cache_key: str

    def __init__(
            self,
            user_repository: UserRepository | None = None,
            external_auth: ExternalAuth | None = None
    ):
        self._user_repository = user_repository or DjangoUserRepository()
        self._jwks_cache_key = "jwks"
        self._cache_storage=DjangoCacheStorage(settings.RESOLVED_ENV["CLERK_CACHE_KEY"])
        self._external_auth = external_auth or ClerkAuth(
            issuer_url=settings.RESOLVED_ENV["CLERK_API_URL"],
            secret_key=settings.RESOLVED_ENV["CLERK_SECRET_KEY"],
            api_base_url="https://api.clerk.com/v1",
        )

    async def _get_user_from_api(self, token: str) -> UserEntity:
        auth_jwks = await self._cache_storage.get_data(self._external_auth.get_jwks, self._jwks_cache_key)
        principal = decode_jwt_contents(token, auth_jwks)
        external_user = await self._external_auth.fetch_user_info(principal.external_user_id)
        internal_user = await self._user_repository.get_or_create_by_external_id(principal.external_user_id)
        internal_user.sync_with_external(external_user)
        return await self._user_repository.update_user_info(internal_user)

    def _build_user_hash(self, token: str) -> str:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return f"user_{token_hash}"

    async def handle(self, command: AuthenticateUserCommand) -> tuple[User, str] | None:
        token = self._external_auth.resolve_auth_token(command.auth_header)
        if not token:
            return None

        user_entity: UserEntity = await self._cache_storage.get_data(
            lambda: self._get_user_from_api(token),
            self._build_user_hash(token),
        )
        user_model = await self._user_repository.get_user_raw(user_entity)
        return user_model, token