from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedResource

from .cache_worker import CacheWorker
from .dtos import GetNotificationQuery, NotificationDTO
from .exceptions import NotificationNotFoundError
from .infra import fetch_owned_notification, get_redis_client
from .logger_shortcuts import log_served_from_cache, log_served_from_store


class GetNotificationQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: GetNotificationQuery) -> FetchedResource:
        cached_value = await self._cache_worker.try_serve_from_cache(
            query.notification_id,
            query.user_id,
        )
        if cached_value is not None:
            log_served_from_cache(query.notification_id)
            return FetchedResource(resource=cached_value, cached=True)

        owned_notification = await fetch_owned_notification(
            query.user_id,
            query.notification_id,
        )
        if owned_notification is None:
            raise NotificationNotFoundError()

        notification = NotificationDTO.from_read_model(owned_notification)
        await self._cache_worker.save_to_cache(notification)

        log_served_from_store(query.notification_id)
        return FetchedResource(resource=notification, cached=False)
