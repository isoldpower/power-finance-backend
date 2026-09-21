from opentelemetry import propagate
from opentelemetry.context import Context

from .carrier import KafkaHeaderPairs, TextMapCarrier, kafka_header_carrier_getter


def inject_current_context() -> TextMapCarrier:
    carrier: TextMapCarrier = {}
    propagate.inject(carrier)

    return carrier


def extract_context_from_text_map(carrier: TextMapCarrier) -> Context:
    return propagate.extract(carrier)


def extract_context_from_kafka_headers(headers: KafkaHeaderPairs) -> Context:
    return propagate.extract(headers, getter=kafka_header_carrier_getter)
