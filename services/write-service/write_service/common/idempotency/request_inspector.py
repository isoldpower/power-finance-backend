from typing import Any

IDEMPOTENCY_HEADER = "Idempotency-Key"
_MAX_KEY_LENGTH = 255
_ANONYMOUS_USER_ID = "anonymous"


class RequestInspector:
    @staticmethod
    def extract_idempotency_key(request: Any) -> str | None:
        raw_value = request.headers.get(IDEMPOTENCY_HEADER)
        if raw_value is None:
            return None
        stripped_value = raw_value.strip()
        if not stripped_value:
            return None
        return stripped_value[:_MAX_KEY_LENGTH]

    @staticmethod
    def extract_user_id(request: Any) -> int | str:
        user = getattr(request, "user", None)
        user_id = getattr(user, "unique_id", None)
        if user_id is None:
            return _ANONYMOUS_USER_ID
        return user_id
