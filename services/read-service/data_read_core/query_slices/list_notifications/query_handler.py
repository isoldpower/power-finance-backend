from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedRows

from .cache_worker import CacheWorker
from .dtos import (
    CacheOperationData,
    ListNotificationsQuery,
    NotificationDTO,
)
from .infra import (
    count_owned_notifications,
    fetch_owned_notifications,
    get_redis_client,
)
from .logger_shortcuts import (
    log_served_from_cache,
    log_served_from_store,
)


class ListNotificationsQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: ListNotificationsQuery) -> FetchedRows:
        cache_operation = self._build_cache_operation(query)
        cached_value = await self._cache_worker.try_serve_from_cache(cache_operation)
        if cached_value is not None:
            notifications, total = cached_value
            log_served_from_cache(query.user_id)
            return FetchedRows(
                rows=notifications,
                total=total,
                cached=True,
            )

        notifications, total = await self._make_store_request(query)
        await self._cache_worker.save_to_cache(
            context=cache_operation,
            notifications=notifications,
            total=total,
        )

        log_served_from_store(
            query.user_id,
            notifications,
            total,
        )
        return FetchedRows(
            rows=notifications,
            total=total,
            cached=False,
        )

    async def _make_store_request(
        self, query: ListNotificationsQuery
    ) -> tuple[list[NotificationDTO], int]:
        only_unread = bool(query.filters.get("only_unread", False))
        total = await count_owned_notifications(query.user_id, only_unread)
        database_entry = await fetch_owned_notifications(
            query.user_id,
            query.page,
            only_unread,
        )

        notifications = [NotificationDTO.from_read_model(entry) for entry in database_entry]
        return notifications, total

    def _build_cache_operation(self, query: ListNotificationsQuery) -> CacheOperationData:
        return CacheOperationData(
            user_id=query.user_id,
            filters=query.filters,
            limit=query.page.limit,
            cursor=query.page.cache_token,
        )
