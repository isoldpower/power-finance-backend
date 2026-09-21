from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedResource
from data_read_core.shared.timestamps import period_bounds

from .cache_worker import CacheWorker
from .dtos import (
    GetWalletQuery,
    PeriodFlowsAnalysis,
    RecentTransactionDTO,
    WalletDetailDTO,
    WalletDTO,
)
from .exceptions import WalletNotFoundError
from .infra import (
    count_recent_transactions,
    fetch_owned_wallet,
    fetch_recent_transactions,
    get_redis_client,
    sum_wallet_flows,
)
from .logger_shortcuts import log_served_from_cache, log_served_from_store


class GetWalletQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: GetWalletQuery) -> FetchedResource:
        wallet, cached = await self._load_wallet(query)
        recent_rows = await fetch_recent_transactions(query.wallet_id, query.recent_page)
        recent_total = await count_recent_transactions(query.wallet_id)

        return FetchedResource(
            resource=WalletDetailDTO(
                wallet=wallet,
                period=await self._period_flows(query),
                recent=[RecentTransactionDTO.from_read_model(row) for row in recent_rows],
                recent_total=recent_total,
            ),
            cached=cached,
        )

    async def _load_wallet(self, query: GetWalletQuery) -> tuple[WalletDTO, bool]:
        cached_value = await self._cache_worker.try_serve_from_cache(
            query.wallet_id,
            query.user_id,
        )
        if cached_value is not None:
            log_served_from_cache(query.wallet_id)
            return cached_value, True

        owned_wallet = await fetch_owned_wallet(query.user_id, query.wallet_id)
        if owned_wallet is None:
            raise WalletNotFoundError()

        wallet = WalletDTO.from_read_model(owned_wallet)
        await self._cache_worker.save_to_cache(wallet)

        log_served_from_store(query.wallet_id)
        return wallet, False

    @staticmethod
    async def _period_flows(query: GetWalletQuery) -> PeriodFlowsAnalysis:
        since, until = period_bounds(query.period, query.zone)
        inflow, outflow = await sum_wallet_flows(query.wallet_id, since, until)

        return PeriodFlowsAnalysis(inflow=inflow, outflow=outflow)
