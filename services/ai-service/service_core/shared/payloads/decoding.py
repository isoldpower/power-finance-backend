from typing import TypeVar

from google.protobuf.json_format import Parse, ParseError
from google.protobuf.message import Message
from kafka_client_py import PoisonError
from kafka_consumer_py import EventMessage

TPayload = TypeVar("TPayload", bound=Message)


def decode_payload(event: EventMessage, payload_type: type[TPayload]) -> TPayload:
    payload = payload_type()

    try:
        Parse(event.payload, payload)
    except ParseError as parse_error:
        raise PoisonError(
            f"Event {event.event_id} does not hold a valid {payload_type.__name__} payload"
        ) from parse_error

    return payload
