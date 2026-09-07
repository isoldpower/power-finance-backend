from typing import Any

from .config import ANONYMOUS_USER_ID, HeaderName, IdempotencySettings


class RequestInspector:
    @staticmethod
    def extract_idempotency_key(request: Any) -> str | None:
        raw_value = request.headers.get(HeaderName.IDEMPOTENCY_KEY)
        if raw_value is None:
            return None
        stripped_value = raw_value.strip()
        if not stripped_value:
            return None
        return stripped_value[: IdempotencySettings.MAX_KEY_LENGTH]

    @staticmethod
    def extract_user_id(request: Any) -> int | str:
        user = getattr(request, "user", None)
        user_id = getattr(user, "unique_id", None)
        if user_id is None:
            return ANONYMOUS_USER_ID
        return user_id
