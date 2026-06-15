import asyncio
from dataclasses import dataclass

from ..bootstrap import get_repository_registry
from ..dtos import WebhookDTO, webhook_to_dto
from ..interfaces import WebhookRepository


@dataclass(frozen=True)
class ListFallbackWebhooksQuery:
    user_id: int
    limit: int
    offset: int


class ListFallbackWebhooksQueryHandler:
    def __init__(self, webhook_repository: WebhookRepository | None = None) -> None:
        self._webhook_repository = (
            webhook_repository or get_repository_registry().webhook_repository
        )

    async def handle(self, query: ListFallbackWebhooksQuery) -> tuple[list[WebhookDTO], int]:
        webhooks, total = await asyncio.gather(
            self._webhook_repository.get_user_webhooks(
                user_id=query.user_id,
                limit=query.limit,
                offset=query.offset,
            ),
            self._webhook_repository.count_user_webhooks(query.user_id),
        )

        return [webhook_to_dto(webhook) for webhook in webhooks], total
