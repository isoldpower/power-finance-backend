from drf_spectacular.extensions import OpenApiAuthenticationExtension

from .config import SchemaName


class GatewayUserHeaderAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = (
        "data_write_core.presentation.http.auth.gateway_authentication."
        "GatewayUserHeaderAuthentication"
    )
    name = str(SchemaName.SECURITY)

    def get_security_definition(self, auto_schema) -> dict:
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Clerk session token. The gateway verifies it and forwards the "
                "resolved user to this service; requests that do not traverse "
                "the gateway are rejected with 401."
            ),
        }
