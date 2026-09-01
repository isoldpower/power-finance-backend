from data_write_core.domain.entities import ActionEntity, rank_of
from data_write_core.domain.events import EventCollector
from data_write_core.domain.value_objects import ActionResolution
from data_write_core.infrastructure.orm import ActionModel


class ActionMapper:
    @staticmethod
    def to_domain(model: ActionModel) -> ActionEntity:
        return ActionEntity(
            id=str(model.id),
            user_id=str(model.user_id),
            user_external_id=model.user_external_id,
            source=model.source,
            kind=model.kind,
            severity=model.severity,
            status=model.status,
            title=model.title,
            body=model.body,
            subject_type=model.subject_type or None,
            subject_id=model.subject_id or None,
            money_amount=model.money_amount,
            money_currency=model.money_currency or None,
            group_key=model.group_key or None,
            occurrences=model.occurrences,
            last_seen_at=model.last_seen_at,
            expires_at=model.expires_at,
            resolved_at=model.resolved_at,
            resolution_id=model.resolution_id or None,
            resolutions=tuple(
                ActionResolution.from_storage(raw) for raw in model.resolutions or []
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
            event_collector=EventCollector(),
        )

    @staticmethod
    def apply_to_model(model: ActionModel, entity: ActionEntity) -> ActionModel:
        model.id = entity.unique_id
        model.user_id = int(entity.user_id)
        model.user_external_id = entity.user_external_id
        model.source = entity.source
        model.kind = entity.kind
        model.severity = entity.severity
        model.severity_rank = rank_of(entity.severity)
        model.status = entity.status
        model.title = entity.title
        model.body = entity.body
        model.subject_type = entity.subject_type or ""
        model.subject_id = entity.subject_id or ""
        model.money_amount = entity.money_amount
        model.money_currency = entity.money_currency or ""
        model.group_key = entity.group_key or ""
        model.occurrences = entity.occurrences
        model.last_seen_at = entity.last_seen_at
        model.expires_at = entity.expires_at
        model.resolved_at = entity.resolved_at
        model.resolution_id = entity.resolution_id or ""
        model.resolutions = [resolution.to_storage() for resolution in entity.resolutions]
        model.created_at = entity.created_at
        model.updated_at = entity.updated_at

        return model
