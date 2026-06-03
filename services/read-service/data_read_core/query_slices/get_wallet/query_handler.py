import json
from logging import getLogger

from redis.asyncio import Redis

from .dtos import GetWalletQuery, WalletDTO
from .exceptions import WalletNotFoundError
from .infra import (
    fetch_owned_wallet,
    get_redis_client,
    get_single_cache_key,
)

logger = getLogger("query_slices.get_wallet")

CACHE_TTL_SECONDS = 300


class GetWalletQueryHandler:
    def __init__(
        self,
        redis_client: Redis | None = None,
    ):
        self._redis_client = redis_client or get_redis_client()

    async def handle(self, query: GetWalletQuery) -> WalletDTO:
        cached_value = await self._try_retrieve_from_cache(query.wallet_id, query.user_id)
        if cached_value is not None:
            return cached_value

        model = await fetch_owned_wallet(query.user_id, query.wallet_id)
        if model is None:
            raise WalletNotFoundError(
                f"Wallet {query.wallet_id} not found for user {query.user_id}"
            )

        wallet = WalletDTO.from_read_model(model)
        await self._save_to_cache(wallet)

        logger.info("Served wallet %s from read store.", query.wallet_id)
        return wallet

    async def _try_retrieve_from_cache(self, wallet_id: str, user_id: int) -> WalletDTO | None:
        cache_key = get_single_cache_key(wallet_id)
        cached_value = await self._redis_client.get(cache_key)

        if cached_value is not None:
            wallet = WalletDTO.from_cache(json.loads(cached_value))

            if wallet.user_id == user_id:
                logger.info("Served wallet %s from cache.", wallet_id)
                return wallet
            else:
                await self._redis_client.delete(cache_key)

        return None

    async def _save_to_cache(self, wallet: WalletDTO) -> None:
        cache_key = get_single_cache_key(wallet.id)
        await self._redis_client.set(
            cache_key,
            json.dumps(wallet.to_cache()),
            ex=CACHE_TTL_SECONDS,
        )
