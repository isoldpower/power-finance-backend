from redis.asyncio import Redis

from .cache_worker import CacheWorker
from .dtos import CacheOperationData, ListWebhooksQuery, WebhookDTO
from .infra import count_owned_webhooks, fetch_owned_webhooks, get_redis_client
from .logger_shortcuts import log_served_from_cache, log_served_from_store


class ListWebhooksQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: ListWebhooksQuery) -> tuple[list[WebhookDTO], int]:
        cache_operation = CacheOperationData(
            user_id=query.user_id,
            limit=query.limit,
            offset=query.offset,
        )
        cached_value = await self._cache_worker.try_serve_from_cache(cache_operation)
        if cached_value is not None:
            log_served_from_cache(query.user_id)
            return cached_value

        total = await count_owned_webhooks(query.user_id)
        database_entry = await fetch_owned_webhooks(query.user_id, query.limit, query.offset)
        webhooks = [WebhookDTO.from_read_model(entry) for entry in database_entry]
        await self._cache_worker.save_to_cache(
            context=cache_operation,
            webhooks=webhooks,
            total=total,
        )

        log_served_from_store(query.user_id, webhooks, total)
        return webhooks, total
