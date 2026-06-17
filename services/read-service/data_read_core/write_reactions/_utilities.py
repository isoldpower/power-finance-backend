from collections.abc import Awaitable, Callable
from typing import TypeVar

from django.db import DataError, IntegrityError
from google.protobuf.json_format import Parse, ParseError
from google.protobuf.message import Message
from kafka_client_py import PoisonError

from data_read_core.shared.kafka_updates import EventMessage
from data_read_core.shared.postgres_orm import aatomic

from ._logger_shortcuts import (
    except_constraint_violation,
    except_service_model_mismatch,
)

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
        async with aatomic():
            return await effect(payload)
    except IntegrityError:
        except_service_model_mismatch(resource_id)
    except DataError:
        except_constraint_violation(resource_id)

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
