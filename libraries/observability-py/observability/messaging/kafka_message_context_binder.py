from contextvars import Token
from typing import cast

from opentelemetry import context as context_api
from opentelemetry.context import Context

from ..context import KafkaHeaderPairs, extract_context_from_kafka_headers
from ..sandbox import read_sandbox_id_from_context


class KafkaMessageContextBinder:
    def bind(self, headers: KafkaHeaderPairs) -> object:
        return context_api.attach(extract_context_from_kafka_headers(headers))

    def unbind(self, attachment_token: object) -> None:
        context_api.detach(cast(Token[Context], attachment_token))

    def read_sandbox_id(self, headers: KafkaHeaderPairs) -> str | None:
        return read_sandbox_id_from_context(extract_context_from_kafka_headers(headers))
