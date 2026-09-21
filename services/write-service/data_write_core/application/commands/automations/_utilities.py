from typing import Any

from data_write_core.domain.entities import AutomationEffect, AutomationTrigger


def trigger_from(raw: dict[str, Any]) -> AutomationTrigger:
    return AutomationTrigger(
        type=raw["type"],
        event=raw.get("event"),
        schedule=raw.get("schedule"),
        filter_body=raw.get("filter_body"),
    )


def effects_from(raw: list[dict[str, Any]]) -> tuple[AutomationEffect, ...]:
    return tuple(AutomationEffect(type=item["type"], params=item["params"]) for item in raw)
