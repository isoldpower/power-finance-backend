from rest_framework.response import Response

from .atomic_redis import StoredResponse
from .replay_marker import mark_replay

REPLAY_HEADER = "Idempotent-Replayed"


class ReplayResponseBuilder:
    @staticmethod
    def build(stored_response: StoredResponse) -> Response:
        rebuilt_response = Response(
            data=stored_response.body,
            status=stored_response.status_code,
        )
        for header_name, header_value in stored_response.headers.items():
            rebuilt_response[header_name] = header_value

        rebuilt_response[REPLAY_HEADER] = "true"

        return mark_replay(
            rebuilt_response,
            replayed=True,
        )
