from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist

from data_write_core.domain.exceptions import WebhookNotFoundError

from ..bootstrap import get_repository_registry
from ..dtos import (
    WebhookDTO,
    WebhookSubscriptionDTO,
    webhook_subscription_to_dto,
    webhook_to_dto,
)
from ..interfaces import WebhookRepository


@dataclass(frozen=True)
class GetFallbackWebhookQuery:
    user_id: int
    webhook_id: UUID


class GetFallbackWebhookQueryHandler:
    def __init__(self, webhook_repository: WebhookRepository | None = None) -> None:
        self._webhook_repository = (
            webhook_repository or get_repository_registry().webhook_repository
        )

    async def handle(self, query: GetFallbackWebhookQuery) -> WebhookDTO:
        try:
            webhook = await self._webhook_repository.get_user_webhook_by_id(
                webhook_id=query.webhook_id,
                user_id=query.user_id,
            )
        except ObjectDoesNotExist as exc:
            raise WebhookNotFoundError(query.webhook_id) from exc

        return webhook_to_dto(webhook)


@dataclass(frozen=True)
class ListFallbackWebhookSubscriptionsQuery:
    user_id: int
    webhook_id: UUID


class ListFallbackWebhookSubscriptionsQueryHandler:
    def __init__(self, webhook_repository: WebhookRepository | None = None) -> None:
        self._webhook_repository = (
            webhook_repository or get_repository_registry().webhook_repository
        )

    async def handle(
        self, query: ListFallbackWebhookSubscriptionsQuery
    ) -> list[WebhookSubscriptionDTO]:
        try:
            await self._webhook_repository.get_user_webhook_by_id(
                webhook_id=query.webhook_id,
                user_id=query.user_id,
            )
        except ObjectDoesNotExist as exc:
            raise WebhookNotFoundError(query.webhook_id) from exc

        subscriptions = await self._webhook_repository.get_webhook_subscriptions(
            query.webhook_id,
        )

        return [webhook_subscription_to_dto(subscription) for subscription in subscriptions]
