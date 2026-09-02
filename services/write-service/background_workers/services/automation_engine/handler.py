"""The consumer callback: decode the envelope, find the handler, delegate.

Every outbox event lands on this topic, so an event no handler serves is
ordinary traffic rather than a broken message.
"""

import logging

from kafka_client_py import ConsumedMessage, PoisonError
from kafka_consumer_py import MalformedEnvelope, OutboxEnvelopeDecoder

from .event_handlers import EVENT_AUTOMATION_HANDLERS

logger = logging.getLogger("background_workers.automation_engine")

_DECODER = OutboxEnvelopeDecoder()


async def handle_automation_event(message: ConsumedMessage) -> None:
    try:
        event = _DECODER.decode(message)
    except MalformedEnvelope as broken:
        raise PoisonError(str(broken)) from broken

    handler = EVENT_AUTOMATION_HANDLERS.get(event.event_type)
    if handler is None:
        return

    applied = await handler.handle(event)
    if applied:
        logger.info(
            "automation_engine: %d rule(s) applied to a %s event",
            len(applied),
            event.event_type,
        )
