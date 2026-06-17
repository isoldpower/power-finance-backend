from data_write_core.domain.entities import WebhookEntity, WebhookSubscriptionEntity
from data_write_core.domain.events import EventCollector
from data_write_core.infrastructure.orm import WebhookModel, WebhookSubscriptionModel


class WebhookMapper:
    @staticmethod
    def to_domain(model: WebhookModel) -> WebhookEntity:
        return WebhookEntity(
            id=str(model.id),
            title=model.title,
            url=model.url,
            secret=model.secret,
            is_active=model.is_active,
            user_id=str(model.user_id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            event_collector=EventCollector(),
        )

    @staticmethod
    def apply_to_model(model: WebhookModel, entity: WebhookEntity) -> WebhookModel:
        model.id = entity.unique_id
        model.title = entity.title
        model.url = entity.url
        model.secret = entity.secret
        model.is_active = entity.is_active
        model.user_id = int(entity.user_id)
        model.created_at = entity.created_at

        return model


class WebhookSubscriptionMapper:
    @staticmethod
    def to_domain(model: WebhookSubscriptionModel) -> WebhookSubscriptionEntity:
        return WebhookSubscriptionEntity(
            id=str(model.id),
            webhook_id=str(model.webhook_id),
            event_type=model.event_type,
            is_active=model.is_active,
            created_at=model.created_at,
            event_collector=EventCollector(),
        )

    @staticmethod
    def apply_to_model(
        model: WebhookSubscriptionModel,
        entity: WebhookSubscriptionEntity,
    ) -> WebhookSubscriptionModel:
        model.id = entity.unique_id
        model.webhook_id = entity.webhook_id
        model.event_type = entity.event_type
        model.is_active = entity.is_active
        model.created_at = entity.created_at

        return model
