from finances.application.dtos import WebhookSubscriptionDTO
from finances.domain.entities import Webhook

from .update_mapper import UpdateMapper
from ..orm import WebhookEndpointModel, WebhookEventSubscriptionModel


class WebhookMapper:
    WEBHOOK_EDITABLE_MAP: list[tuple[str, str]] = [
        ('user_id', 'user_id'),
        ('title', 'title'),
        ('url', 'url'),
        ('is_active', 'is_active'),
        ('secret', 'secret'),
    ]

    @staticmethod
    def update_model(
            model: WebhookEndpointModel,
            entity: Webhook,
            replace: bool = False,
    ) -> WebhookEndpointModel:
        return UpdateMapper[WebhookEndpointModel, Webhook].update_model(
            model,
            entity,
            WebhookMapper.WEBHOOK_EDITABLE_MAP,
            replace
        )

    @staticmethod
    def to_domain(model: WebhookEndpointModel) -> Webhook:
        return Webhook.from_persistence(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            url=model.url,
            is_active=model.is_active,
            secret=model.secret,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def subscription_to_dto(model: WebhookEventSubscriptionModel) -> WebhookSubscriptionDTO:
        return WebhookSubscriptionDTO(
            id=model.id,
            event_type=model.event_type,
            endpoint_id=model.endpoint_id,
            is_active=model.is_active,
        )

    @staticmethod
    def get_changed_fields(model: WebhookEndpointModel, entity: Webhook) -> list[str]:
        return UpdateMapper[WebhookEndpointModel, Webhook].get_changed_fields(
            model,
            entity,
            WebhookMapper.WEBHOOK_EDITABLE_MAP,
            updated_list=["updated_at"]
        )