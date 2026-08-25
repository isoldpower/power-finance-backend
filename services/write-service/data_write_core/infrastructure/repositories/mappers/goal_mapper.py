from data_write_core.domain.entities import GoalEntity
from data_write_core.domain.events import EventCollector
from data_write_core.infrastructure.orm import GoalModel


class GoalMapper:
    @staticmethod
    def to_domain(model: GoalModel) -> GoalEntity:
        return GoalEntity(
            id=str(model.id),
            title=model.name,
            currency_code=model.currency_id,
            target=model.target,
            finish_at=model.finish_at,
            url=model.url,
            user_id=str(model.user_id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            event_collector=EventCollector(),
        )

    @staticmethod
    def apply_to_model(model: GoalModel, entity: GoalEntity) -> GoalModel:
        model.id = entity.unique_id
        model.name = entity.title
        model.currency_id = entity.currency_code
        model.target = entity.target
        model.finish_at = entity.finish_at
        model.url = entity.url
        model.user_id = int(entity.user_id)
        model.created_at = entity.created_at
        model.updated_at = entity.updated_at
        model.deleted_at = entity.deleted_at

        return model
