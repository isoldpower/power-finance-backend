from drf_spectacular.extensions import OpenApiAuthenticationExtension
from identity.infrastructure.auth_integration.drf_jwt_authentication import ClerkJWTAuthentication

class ClerkJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = ClerkJWTAuthentication
    name = 'ClerkJWTAuthentication'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
