import json
from datetime import datetime

from kafka_messages import (
    AutomationCreated,
    AutomationDeleted,
    AutomationRan,
    AutomationUpdated,
)
from kafka_messages import (
    AutomationEffect as EffectMessage,
)
from kafka_messages import AutomationTrigger as TriggerMessage

from data_write_core.domain.entities import AutomationEntity
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp

AUTOMATION_AGGREGATE = "automation"


def _trigger_of(automation: AutomationEntity) -> TriggerMessage:
    """`filter_body` crosses as JSON TEXT rather than a Struct: it is opaque to
    every consumer except the engine, and a Struct would invite reading into a
    tree whose grammar is owned elsewhere."""

    return TriggerMessage(
        trigger_type=automation.trigger.type,
        event=automation.trigger.event or "",
        schedule=automation.trigger.schedule or "",
        filter_body_json=(
            json.dumps(automation.trigger.filter_body)
            if automation.trigger.filter_body is not None
            else ""
        ),
    )


def _effects_of(automation: AutomationEntity) -> list[EffectMessage]:
    return [
        EffectMessage(effect_type=effect.type, params_json=json.dumps(effect.params))
        for effect in automation.effects
    ]


def automation_created(automation: AutomationEntity):
    message = AutomationCreated(
        automation_id=automation.unique_id,
        user_external_id=automation.user_external_id,
        user_id=int(automation.user_id),
        name=automation.name,
        icon=automation.icon,
        enabled=automation.enabled,
        trigger=_trigger_of(automation),
        effects=_effects_of(automation),
        created_at=datetime_to_timestamp(automation.created_at),
    )

    return _entry(message, automation)


def automation_updated(automation: AutomationEntity, at: datetime):
    message = AutomationUpdated(
        automation_id=automation.unique_id,
        user_external_id=automation.user_external_id,
        user_id=int(automation.user_id),
        name=automation.name,
        icon=automation.icon,
        enabled=automation.enabled,
        trigger=_trigger_of(automation),
        effects=_effects_of(automation),
        updated_at=datetime_to_timestamp(at),
    )

    return _entry(message, automation)


def automation_deleted(automation: AutomationEntity, at: datetime):
    message = AutomationDeleted(
        automation_id=automation.unique_id,
        user_external_id=automation.user_external_id,
        user_id=int(automation.user_id),
        deleted_at=datetime_to_timestamp(at),
    )

    return _entry(message, automation)


def automation_ran(
    automation_id: str,
    user_id: int,
    user_external_id: str,
    runs: int,
    at: datetime,
):
    """`runs` counts MATCHES that applied effects, not evaluations: a rule
    checked a thousand times that never matched reports 0, which is what makes a
    silently-stopped rule distinguishable from a working one."""

    message = AutomationRan(
        automation_id=automation_id,
        user_external_id=user_external_id,
        user_id=user_id,
        runs=runs,
        last_run_at=datetime_to_timestamp(at),
    )

    return build_outbox_entry(
        message,
        aggregate_type=AUTOMATION_AGGREGATE,
        aggregate_id=automation_id,
        partition_key=user_external_id,
    )


def _entry(message, automation: AutomationEntity):
    return build_outbox_entry(
        message,
        aggregate_type=AUTOMATION_AGGREGATE,
        aggregate_id=automation.unique_id,
        partition_key=automation.user_external_id,
    )
