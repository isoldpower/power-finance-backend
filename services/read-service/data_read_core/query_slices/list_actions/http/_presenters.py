from ..dtos import ActionDTO


def present_one(action: ActionDTO) -> dict:
    return {
        "id": action.id,
        "source": action.source,
        "kind": action.kind,
        "severity": action.severity,
        "status": action.status,
        "title": action.title,
        "body": action.body,
        "subject": _present_subject(action),
        "money": _present_money(action),
        "group_key": action.group_key or None,
        "occurrences": action.occurrences,
        "last_seen_at": action.last_seen_at,
        "expires_at": action.expires_at,
        "resolved_at": action.resolved_at,
        "resolutions": [
            {
                "id": resolution["resolution_id"],
                "label": resolution["label"],
                "intent": resolution["intent"],
                "applies": resolution["applies"],
            }
            for resolution in action.resolutions
        ],
        "created_at": action.created_at,
        "updated_at": action.updated_at,
        "deleted_at": action.deleted_at,
    }


def present_many(actions: list[ActionDTO]) -> list[dict]:
    return [present_one(action) for action in actions]


def _present_subject(action: ActionDTO) -> dict | None:
    if not action.subject_type or not action.subject_id:
        return None

    return {
        "type": action.subject_type,
        "id": action.subject_id,
    }


def _present_money(action: ActionDTO) -> dict | None:
    if action.money_amount is None or not action.money_currency:
        return None

    return {
        "amount": action.money_amount,
        "currency": action.money_currency,
    }
