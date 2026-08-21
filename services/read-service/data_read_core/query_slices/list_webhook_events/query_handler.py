from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedRows

from .cache_worker import CacheWorker
from .dtos import ListWebhookEventsQuery, WebhookSubscriptionDTO
from .exceptions import WebhookNotFoundError
from .infra import fetch_webhook_subscriptions, get_redis_client, webhook_is_owned
from .logger_shortcuts import log_served_from_cache, log_served_from_store


class ListWebhookEventsQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: ListWebhookEventsQuery) -> FetchedRows:
        if not await webhook_is_owned(query.user_id, query.webhook_id):
            raise WebhookNotFoundError()

        cached_value = await self._cache_worker.try_serve_from_cache(query.webhook_id)
        if cached_value is not None:
            log_served_from_cache(query.webhook_id)
            return FetchedRows(
                rows=cached_value,
                total=len(cached_value),
                cached=True,
            )

        subscriptions = await fetch_webhook_subscriptions(query.webhook_id)
        dtos = [WebhookSubscriptionDTO.from_read_model(entry) for entry in subscriptions]
        await self._cache_worker.save_to_cache(query.webhook_id, dtos)

        log_served_from_store(query.webhook_id, len(dtos))
        return FetchedRows(
            rows=dtos,
            total=len(dtos),
            cached=False,
        )
