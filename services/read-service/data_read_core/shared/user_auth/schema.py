from drf_spectacular.extensions import OpenApiAuthenticationExtension

SECURITY_SCHEME_NAME = "clerkBearer"


class GatewayUserHeaderAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = (
        "data_read_core.shared.user_auth.gateway_authentication.GatewayUserHeaderAuthentication"
    )
    name = SECURITY_SCHEME_NAME

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
