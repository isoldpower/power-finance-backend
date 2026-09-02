from write_service.common.timestamps import to_iso

from data_write_core.application.dtos import AutomationDTO


class AutomationHttpPresenter:
    @staticmethod
    def present_one(automation: AutomationDTO) -> dict:
        return {
            "id": str(automation.id),
            "name": automation.name,
            "icon": automation.icon,
            "enabled": automation.enabled,
            "trigger": AutomationHttpPresenter._present_trigger(automation),
            "effects": [
                {"type": effect.type, "params": effect.params} for effect in automation.effects
            ],
            "last_run_at": to_iso(automation.last_run_at),
            "runs": automation.runs,
            "created_at": to_iso(automation.created_at),
            "updated_at": to_iso(automation.updated_at),
            "deleted_at": to_iso(automation.deleted_at),
        }

    @staticmethod
    def present_many(automations: list[AutomationDTO]) -> list[dict]:
        return [AutomationHttpPresenter.present_one(item) for item in automations]

    @staticmethod
    def _present_trigger(automation: AutomationDTO) -> dict:
        """Both `event` and `schedule` are always present, the inapplicable one
        `null` — so a client reads `trigger.schedule` without guarding. Requests
        supply one; responses carry both."""

        return {
            "type": automation.trigger.type,
            "event": automation.trigger.event,
            "schedule": automation.trigger.schedule,
            "filter_body": automation.trigger.filter_body,
        }
