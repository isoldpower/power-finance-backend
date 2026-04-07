from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import User
from identity.presentation.jwt_authentication import ClerkJWTAuthentication


class JWTAuthenticationTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        # Patch the handler class to return a mock instance
        self.handler_patcher = patch("identity.presentation.jwt_authentication.AuthenticateUserCommandHandler")
        self.mock_handler_class = self.handler_patcher.start()
        self.mock_handler_instance = self.mock_handler_class.return_value
        
        self.auth = ClerkJWTAuthentication()

    def tearDown(self):
        self.handler_patcher.stop()

    def test_options_method_skips_authentication(self):
        request = self.factory.options("/api/v1/test/")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_valid_token_returns_user_tuple(self):
        mock_user = MagicMock(spec=User)
        self.mock_handler_instance.handle.return_value = (mock_user, "valid-token")
        
        request = self.factory.get("/api/v1/test/", HTTP_AUTHORIZATION="Bearer valid-token")
        result = self.auth.authenticate(request)
        
        self.assertEqual(result, (mock_user, "valid-token"))

    def test_missing_header_returns_none(self):
        # If handle returns None (e.g. no token resolved), authenticate returns None
        self.mock_handler_instance.handle.return_value = None
        
        request = self.factory.get("/api/v1/test/")
        result = self.auth.authenticate(request)
        
        self.assertIsNone(result)

    def test_handler_exception_raises_authentication_failed(self):
        self.mock_handler_instance.handle.side_effect = Exception("Auth failed")
        
        request = self.factory.get("/api/v1/test/", HTTP_AUTHORIZATION="Bearer invalid")
        
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)
