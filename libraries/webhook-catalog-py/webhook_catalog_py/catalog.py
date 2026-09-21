import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from types import MappingProxyType

CATALOG_PATH = Path(__file__).with_name("catalog.json")


@dataclass(frozen=True)
class WebhookEventType:
    event: str
    subject: str
    description: str
    outbox_types: tuple[str, ...]


@cache
def _load() -> tuple[WebhookEventType, ...]:
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    return tuple(
        WebhookEventType(
            event=row["event"],
            subject=row["subject"],
            description=row["description"],
            outbox_types=tuple(row["outbox_types"]),
        )
        for row in raw["event_types"]
    )


def event_types() -> tuple[WebhookEventType, ...]:
    return _load()


def event_values() -> frozenset[str]:
    return frozenset(entry.event for entry in _load())


def is_known_event(event: str) -> bool:
    return event in event_values()


@cache
def _by_outbox_type() -> Mapping[str, str]:
    mapping: dict[str, str] = {}
    for entry in _load():
        for outbox_type in entry.outbox_types:
            mapping[outbox_type] = entry.event

    return MappingProxyType(mapping)


def event_for_outbox_type(outbox_type: str) -> str | None:
    return _by_outbox_type().get(outbox_type)
