from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from data_write_core.domain.events import DomainEvent


def _coerce(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _coerce(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_coerce(item) for item in value]
    return value


def event_to_payload(event: DomainEvent) -> dict[str, Any]:
    return _coerce(asdict(event))
