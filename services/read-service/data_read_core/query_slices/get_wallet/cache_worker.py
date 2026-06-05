import json

from redis.asyncio import Redis

from .dtos import WalletDTO
from .infra import (
    CACHE_TTL_SECONDS,
    get_single_cache_key,
)


class CacheWorker:
    def __init__(self, redis_client: Redis) -> None:
        self._redis_client = redis_client

    async def try_serve_from_cache(self, wallet_id: str, user_id: int) -> WalletDTO | None:
        cache_key = get_single_cache_key(wallet_id)
        cached_value = await self._redis_client.get(cache_key)
        if cached_value is None:
            return None

        wallet = WalletDTO.from_cache(json.loads(cached_value))
        if wallet.user_id != user_id:
            await self._redis_client.delete(cache_key)
            return None

        return wallet

    async def save_to_cache(self, wallet: WalletDTO) -> None:
        cache_key = get_single_cache_key(wallet.id)
        await self._redis_client.set(
            cache_key,
            json.dumps(wallet.to_cache()),
            ex=CACHE_TTL_SECONDS,
        )
