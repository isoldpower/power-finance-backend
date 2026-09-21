import asyncio

from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedResource

from .cache_worker import CacheWorker
from .dtos import (
    AccountDetailDTO,
    AccountDTO,
    GetAccountQuery,
    HistoryEntryDTO,
)
from .exceptions import AccountNotFoundError
from .infra import (
    count_account_history,
    fetch_account_history,
    fetch_owned_account,
    get_redis_client,
)
from .logger_shortcuts import (
    log_served_from_cache,
    log_served_from_store,
)


class GetAccountQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: GetAccountQuery) -> FetchedResource:
        account, cached = await self._load_account(query)
        history_rows, history_total = await asyncio.gather(
            fetch_account_history(account.id, query.history_page),
            count_account_history(account.id),
        )

        return FetchedResource(
            resource=AccountDetailDTO(
                account=account,
                history=[HistoryEntryDTO.from_read_model(row) for row in history_rows],
                history_total=history_total,
            ),
            cached=cached,
        )

    async def _load_account(self, query: GetAccountQuery) -> tuple[AccountDTO, bool]:
        cached_value = await self._cache_worker.try_serve_from_cache(
            query.account_id,
            query.user_id,
        )
        if cached_value is not None:
            log_served_from_cache(query.account_id)
            return cached_value, True

        owned_account = await fetch_owned_account(
            query.user_id,
            query.account_id,
        )
        if owned_account is None:
            raise AccountNotFoundError()

        account = AccountDTO.from_read_model(owned_account)
        await self._cache_worker.save_to_cache(account)

        log_served_from_store(query.account_id)
        return account, False
