import json
from typing import Any


def filter_body_of(raw: str) -> dict[str, Any] | None:
    return json.loads(raw) if raw else None


def effects_of(effects) -> list[dict[str, Any]]:
    return [
        {"type": effect.effect_type, "params": json.loads(effect.params_json or "{}")}
        for effect in effects
    ]
