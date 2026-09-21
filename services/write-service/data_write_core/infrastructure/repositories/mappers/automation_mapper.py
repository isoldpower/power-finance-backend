from data_write_core.domain.entities import (
    AutomationEffect,
    AutomationEntity,
    AutomationTrigger,
)
from data_write_core.domain.events import EventCollector
from data_write_core.infrastructure.orm import AutomationModel


class AutomationMapper:
    @staticmethod
    def to_domain(model: AutomationModel) -> AutomationEntity:
        return AutomationEntity(
            id=str(model.id),
            user_id=str(model.user_id),
            user_external_id=model.user_external_id,
            name=model.name,
            icon=model.icon,
            enabled=model.enabled,
            trigger=AutomationTrigger(
                type=model.trigger_type,
                event=model.trigger_event or None,
                schedule=model.trigger_schedule or None,
                filter_body=model.filter_body,
            ),
            effects=tuple(
                AutomationEffect(type=raw["type"], params=raw["params"])
                for raw in model.effects or []
            ),
            last_run_at=model.last_run_at,
            runs=model.runs,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            event_collector=EventCollector(),
        )

    @staticmethod
    def apply_to_model(model: AutomationModel, entity: AutomationEntity) -> AutomationModel:
        model.id = entity.unique_id
        model.user_id = int(entity.user_id)
        model.user_external_id = entity.user_external_id
        model.name = entity.name
        model.icon = entity.icon
        model.enabled = entity.enabled
        model.trigger_type = entity.trigger.type
        model.trigger_event = entity.trigger.event or ""
        model.trigger_schedule = entity.trigger.schedule or ""
        model.filter_body = entity.trigger.filter_body
        model.effects = [
            {"type": effect.type, "params": effect.params} for effect in entity.effects
        ]
        model.last_run_at = entity.last_run_at
        model.runs = entity.runs
        model.created_at = entity.created_at
        model.updated_at = entity.updated_at
        model.deleted_at = entity.deleted_at

        return model
