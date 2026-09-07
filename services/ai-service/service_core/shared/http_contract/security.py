from fastapi.security import HTTPBearer

from .config import SchemaName

CLERK_BEARER = HTTPBearer(
    scheme_name=str(SchemaName.SECURITY),
    bearerFormat="JWT",
    auto_error=False,
    description=(
        "Clerk session token. The gateway verifies it and forwards the "
        "resolved user to this service; requests that do not traverse "
        "the gateway are rejected with 401."
    ),
)
