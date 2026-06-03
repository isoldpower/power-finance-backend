from collections.abc import Awaitable, Callable
from logging import getLogger
from typing import TypeVar

from django.db import DataError, IntegrityError
from google.protobuf.json_format import Parse, ParseError
from google.protobuf.message import Message
from kafka_client_py import PoisonError

from data_read_core.shared.kafka_updates import EventMessage

logger = getLogger("background_workers.write_message_consumer")

TParams = TypeVar("TParams")
TReturn = TypeVar("TReturn")


async def handle_database_errors(
    effect: Callable[[TParams], Awaitable[TReturn]],
    payload: TParams,
    *,
    resource_id: object,
) -> TReturn | None:
    """Run a read-model write, swallowing misaligned-data DB errors."""

    try:
        return await effect(payload)
    except IntegrityError:
        logger.fatal(
            "Received a resource (id %s) that is breaking read model's schema unique constraints. "
            "It may mean that models are not properly aligned or deduplication failed.",
            resource_id,
        )
    except DataError:
        logger.fatal(
            "Received a resource (id %s) that is breaking read model's boundaries. "
            "It probably means that models are not aligned correctly or noise added to the Kafka message.",
            resource_id,
        )

    return None


TPayload = TypeVar("TPayload", bound=Message)


def decode_payload(event: EventMessage, payload_type: type[TPayload]) -> TPayload:
    """Parse an event into the given proto message type, or raise PoisonError."""

    payload = payload_type()

    if not _parse_event_payload(event, payload):
        raise PoisonError(
            f"Event {event.event_id} does not hold a valid {payload_type.__name__} payload"
        )

    return payload


def _parse_event_payload(event: EventMessage, result: Message) -> bool:
    try:
        Parse(event.payload, result)
        return True
    except ParseError:
        return False
