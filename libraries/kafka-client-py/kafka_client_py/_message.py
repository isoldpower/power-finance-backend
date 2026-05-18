"""Structural type for incoming messages.

Decouples the publishers/handler from aiokafka's concrete `ConsumerRecord`
so they can be unit-tested with plain dataclasses.
"""

from __future__ import annotations

from typing import Protocol

from .headers import KafkaHeaders


class ConsumedMessage(Protocol):
    topic: str
    partition: int
    offset: int
    key: bytes | None
    value: bytes | None
    headers: KafkaHeaders | None
