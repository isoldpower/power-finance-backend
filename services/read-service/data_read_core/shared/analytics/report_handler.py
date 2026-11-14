from abc import ABC, abstractmethod
from typing import Any, Protocol

from redis.asyncio import Redis

from data_read_core.shared.exchange_rates import ExchangeRateService
from data_read_core.shared.query_results import FetchedResource
from data_read_core.shared.redis_cache import get_redis

from .logger_shortcuts import log_served_from_cache, log_served_from_store
from .report_cache import AnalyticsCacheWorker, analytics_version


class AnalyticsQuery(Protocol):
    @property
    def user_id(self) -> int: ...

    @property
    def cache_signature(self) -> dict: ...


class AnalyticsReportHandler[QueryType: AnalyticsQuery](ABC):
    report_name: str
    report_type: type

    def __init__(
        self,
        redis_client: Redis | None = None,
        rate_service: ExchangeRateService | None = None,
    ) -> None:
        self._redis_client = redis_client or get_redis()
        self._cache_worker = AnalyticsCacheWorker(self._redis_client, self.report_name)
        self._rate_service = rate_service

    async def handle(self, query: QueryType) -> FetchedResource:
        version = await analytics_version(query.user_id, self._redis_client)
        cached_report = await self._cache_worker.try_serve_from_cache(
            self.report_type,
            query.user_id,
            version,
            query.cache_signature,
        )
        if cached_report is not None:
            log_served_from_cache(self.report_name, query.user_id)
            return FetchedResource(resource=cached_report, cached=True)

        report = await self._build(query)
        await self._cache_worker.save_to_cache(
            query.user_id,
            version,
            query.cache_signature,
            report,
        )

        log_served_from_store(self.report_name, query.user_id)
        return FetchedResource(resource=report, cached=False)

    @abstractmethod
    async def _build(self, query: QueryType) -> Any:
        raise NotImplementedError()
