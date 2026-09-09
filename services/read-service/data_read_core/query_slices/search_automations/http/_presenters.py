from ..dtos import AutomationDTO


def present_one(automation: AutomationDTO) -> dict:
    return {
        "id": automation.id,
        "name": automation.name,
        "icon": automation.icon,
        "enabled": automation.enabled,
        "trigger": {
            "type": automation.trigger_type,
            "event": automation.trigger_event or None,
            "schedule": automation.trigger_schedule or None,
            "filter_body": automation.filter_body,
        },
        "effects": automation.effects,
        "last_run_at": automation.last_run_at,
        "runs": automation.runs,
        "created_at": automation.created_at,
        "updated_at": automation.updated_at,
        "deleted_at": automation.deleted_at,
    }


def present_many(automations: list[AutomationDTO]) -> list[dict]:
    return [present_one(automation) for automation in automations]
