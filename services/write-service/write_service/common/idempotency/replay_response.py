from rest_framework.response import Response

from .atomic_redis import StoredResponse
from .config import HeaderName
from .replay_marker import mark_replay


class ReplayResponseBuilder:
    @staticmethod
    def build(stored_response: StoredResponse) -> Response:
        rebuilt_response = Response(
            data=stored_response.body,
            status=stored_response.status_code,
        )
        for header_name, header_value in stored_response.headers.items():
            rebuilt_response[header_name] = header_value

        rebuilt_response[HeaderName.REPLAYED] = "true"

        return mark_replay(
            rebuilt_response,
            replayed=True,
        )
