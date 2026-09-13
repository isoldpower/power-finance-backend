from collections.abc import Iterable, Sequence

from opentelemetry.propagators.textmap import Getter

KafkaHeaderPairs = Sequence[tuple[str, bytes | None]]
TextMapCarrier = dict[str, str]


class KafkaHeaderCarrierGetter(Getter[KafkaHeaderPairs]):
    def get(self, carrier: KafkaHeaderPairs, key: str) -> list[str] | None:
        matching_values = [
            decoded_value
            for header_name, header_value in _iterate_headers(carrier)
            if header_name.lower() == key.lower()
            and (decoded_value := _decode_header_value(header_value)) is not None
        ]

        return matching_values or None

    def keys(self, carrier: KafkaHeaderPairs) -> list[str]:
        return [header_name for header_name, _ in _iterate_headers(carrier)]


def _iterate_headers(carrier: KafkaHeaderPairs) -> Iterable[tuple[str, bytes | None]]:
    if not carrier:
        return ()

    return carrier


def _decode_header_value(header_value: bytes | None) -> str | None:
    if header_value is None:
        return None

    try:
        return header_value.decode("utf-8")
    except UnicodeDecodeError:
        return None


kafka_header_carrier_getter = KafkaHeaderCarrierGetter()
