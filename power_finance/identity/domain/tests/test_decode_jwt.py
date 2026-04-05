import jwt
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import SimpleTestCase
from identity.domain.services.decode_jwt import decode_jwt_contents
from identity.application.dtos import AuthenticatedPrincipal


class DecodeJWTTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Generate RSA key pair for testing
        cls.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        cls.public_key = cls.private_key.public_key()
        
        # Prepare JWKS-like data
        public_numbers = cls.public_key.public_numbers()
        cls.jwks_data = {
            "keys": [
                {
                    "kty": "RSA",
                    "alg": "RS256",
                    "use": "sig",
                    "n": jwt.utils.base64url_encode(
                        public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, 'big')
                    ).decode(),
                    "e": jwt.utils.base64url_encode(
                        public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, 'big')
                    ).decode(),
                    "kid": "test-key-id"
                }
            ]
        }

    def test_decode_valid_jwt_returns_principal(self):
        payload = {
            "sub": "user_123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        token = jwt.encode(payload, self.private_key, algorithm="RS256")
        
        result = decode_jwt_contents(token, self.jwks_data)
        
        self.assertIsInstance(result, AuthenticatedPrincipal)
        self.assertEqual(result.external_user_id, "user_123")

    def test_decode_expired_jwt_raises_error(self):
        payload = {
            "sub": "user_123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1)
        }
        token = jwt.encode(payload, self.private_key, algorithm="RS256")
        
        with self.assertRaisesMessage(ValueError, "expired"):
            decode_jwt_contents(token, self.jwks_data)

    def test_decode_corrupted_jwt_raises_error(self):
        token = "not.a.valid.token"
        
        with self.assertRaisesMessage(ValueError, "invalid or corrupted"):
            decode_jwt_contents(token, self.jwks_data)

    def test_decode_jwt_missing_sub_raises_error(self):
        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        token = jwt.encode(payload, self.private_key, algorithm="RS256")
        
        with self.assertRaisesMessage(ValueError, "No account associated"):
            decode_jwt_contents(token, self.jwks_data)
