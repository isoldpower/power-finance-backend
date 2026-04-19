from drf_spectacular.extensions import OpenApiAuthenticationExtension

from .middleware import ClerkJWTAuthentication


class ClerkJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = ClerkJWTAuthentication
    name = 'ClerkJWTAuthentication'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
