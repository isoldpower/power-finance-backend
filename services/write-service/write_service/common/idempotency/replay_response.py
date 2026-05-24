from rest_framework.response import Response

from .atomic_redis import StoredResponse

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
        return rebuilt_response
