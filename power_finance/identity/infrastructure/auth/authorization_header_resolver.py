from rest_framework.exceptions import AuthenticationFailed


def resolve_bearer_token(request) -> str | None:
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None

    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationFailed("Authorization token format is invalid. Expected Bearer token.")
    else:
        return parts[1]