from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from django.contrib.auth import get_user_model
from identity.application.use_cases.authenticate_user import AuthenticateUserCommandHandler, AuthenticateUserCommand
from identity.application.dtos.authentication import AuthenticatedPrincipal, ExternalUserInfo
from identity.domain.entities.user import UserEntity
from identity.infrastructure.repositories.django_user_repository import DjangoUserRepository
from identity.infrastructure.integration import ClerkAuth

User = get_user_model()

class AuthenticateUserTests(SimpleTestCase):
    def setUp(self):
        self.user_repo = MagicMock(spec=DjangoUserRepository)
        self.external_auth = MagicMock(spec=ClerkAuth)
        self.mock_cache = MagicMock()
        
        # Patching settings and CacheStorage to avoid DB/Network hits during init
        self.settings_patcher = patch("django.conf.settings.RESOLVED_ENV", {"CLERK_CACHE_KEY": "test", "CLERK_API_URL": "http://test", "CLERK_SECRET_KEY": "test"})
        self.cache_patcher = patch("identity.application.use_cases.authenticate_user.DjangoCacheStorage", return_value=self.mock_cache)
        
        self.settings_patcher.start()
        self.cache_patcher.start()
        
        self.handler = AuthenticateUserCommandHandler(
            user_repository=self.user_repo,
            external_auth=self.external_auth
        )

    def tearDown(self):
        self.settings_patcher.stop()
        self.cache_patcher.stop()

    def test_no_token_returns_none(self):
        self.external_auth.resolve_auth_token.return_value = None
        command = AuthenticateUserCommand(auth_header="Invalid")
        
        result = self.handler.handle(command)
        
        self.assertIsNone(result)

    @patch("identity.application.use_cases.authenticate_user.decode_jwt_contents")
    def test_cache_miss_fetches_from_api(self, mock_decode):
        # get_data calls the lambda if cache miss
        self.mock_cache.get_data.side_effect = lambda func, key: func()
        
        token = "valid-token"
        self.external_auth.resolve_auth_token.return_value = token
        mock_decode.return_value = AuthenticatedPrincipal(external_user_id="user_123")
        
        external_info = ExternalUserInfo(
            external_user_id="user_123",
            email_address="test@example.com",
            first_name="First",
            last_name="Last",
            last_login=None
        )
        self.external_auth.fetch_user_info.return_value = external_info
        
        user_entity = UserEntity(
            id="user_123",
            email="test@example.com",
            first_name="First",
            last_name="Last",
            last_login=None
        )
        self.user_repo.get_or_create_by_external_id.return_value = user_entity
        self.user_repo.update_user_info.return_value = user_entity
        
        mock_user_model = MagicMock(spec=User)
        self.user_repo.get_user_raw.return_value = mock_user_model
        
        command = AuthenticateUserCommand(auth_header="Bearer valid-token")
        result = self.handler.handle(command)
        
        self.assertEqual(result, (mock_user_model, token))
        self.external_auth.fetch_user_info.assert_called_once_with("user_123")
        self.user_repo.get_or_create_by_external_id.assert_called_once_with("user_123")

    def test_cache_hit_uses_cached_data(self):
        user_entity = UserEntity(
            id="user_123",
            email="test@example.com",
            first_name="First",
            last_name="Last",
            last_login=None
        )
        # get_data returns the cached value directly
        self.mock_cache.get_data.return_value = user_entity
        
        token = "valid-token"
        self.external_auth.resolve_auth_token.return_value = token
        
        mock_user_model = MagicMock(spec=User)
        self.user_repo.get_user_raw.return_value = mock_user_model
        
        command = AuthenticateUserCommand(auth_header="Bearer valid-token")
        result = self.handler.handle(command)
        
        self.assertEqual(result, (mock_user_model, token))
        self.external_auth.fetch_user_info.assert_not_called()
        self.user_repo.get_user_raw.assert_called_once_with(user_entity)
