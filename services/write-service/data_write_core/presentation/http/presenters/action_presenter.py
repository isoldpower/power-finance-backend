from write_service.common.timestamps import to_iso

from data_write_core.application.dtos import ActionDTO


class ActionHttpPresenter:
    @staticmethod
    def present_one(action: ActionDTO) -> dict:
        return {
            "id": str(action.id),
            "source": action.source,
            "kind": action.kind,
            "severity": action.severity,
            "status": action.status,
            "title": action.title,
            "body": action.body,
            "subject": ActionHttpPresenter._present_subject(action),
            "money": ActionHttpPresenter._present_money(action),
            "group_key": action.group_key,
            "occurrences": action.occurrences,
            "last_seen_at": to_iso(action.last_seen_at),
            "expires_at": to_iso(action.expires_at),
            "resolved_at": to_iso(action.resolved_at),
            "resolutions": [
                {
                    "id": resolution.resolution_id,
                    "label": resolution.label,
                    "intent": resolution.intent,
                    "applies": resolution.applies,
                }
                for resolution in action.resolutions
            ],
            "created_at": to_iso(action.created_at),
            "updated_at": to_iso(action.updated_at),
            "deleted_at": to_iso(action.deleted_at),
        }

    @staticmethod
    def present_many(actions: list[ActionDTO]) -> list[dict]:
        return [ActionHttpPresenter.present_one(action) for action in actions]

    @staticmethod
    def _present_subject(action: ActionDTO) -> dict | None:
        if not action.subject_type or not action.subject_id:
            return None

        return {"type": action.subject_type, "id": action.subject_id}

    @staticmethod
    def _present_money(action: ActionDTO) -> dict | None:
        """The amount at stake, in the currency the action concerns. NOT
        converted to any reporting currency — this is not Metrics."""

        if action.money_amount is None or not action.money_currency:
            return None

        return {
            "amount": str(action.money_amount),
            "currency": action.money_currency,
        }
