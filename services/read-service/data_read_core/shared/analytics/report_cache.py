import hashlib
import json
from typing import Any

from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

from .config import CacheSchema, CacheSettings
from .dataclass_codec import decode_from_cache, encode_for_cache

TRANSACTION_VERSION_KEY = "ver:transactions:{user_id}"
WALLET_VERSION_KEY = "ver:wallets:{user_id}"


def get_transaction_version_key(user_id: int) -> str:
    return TRANSACTION_VERSION_KEY.format(user_id=user_id)


def get_wallet_version_key(user_id: int) -> str:
    return WALLET_VERSION_KEY.format(user_id=user_id)


def get_parameters_hash(parameters: dict) -> str:
    canonical = json.dumps(parameters, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(canonical.encode()).hexdigest()[:16]


def get_analytics_cache_key(
    report_name: str,
    user_id: int,
    version: str,
    parameters_hash: str,
) -> str:
    return (
        f"read:analytics:{CacheSchema.VERSION}:{report_name}:{user_id}"
        f":v{version}:p{parameters_hash}"
    )


async def analytics_version(user_id: int, redis_client: Redis | None = None) -> str:
    transactions_version, wallets_version = await (redis_client or get_redis()).mget(
        get_transaction_version_key(user_id),
        get_wallet_version_key(user_id),
    )

    return f"{_as_version(transactions_version)}.{_as_version(wallets_version)}"


class AnalyticsCacheWorker:
    def __init__(self, redis_client: Redis, report_name: str) -> None:
        self._redis_client = redis_client
        self._report_name = report_name

    async def try_serve_from_cache(
        self,
        report_type: type,
        user_id: int,
        version: str,
        parameters: dict,
    ) -> Any | None:
        cached_value = await self._redis_client.get(self._key_for(user_id, version, parameters))
        if cached_value is None:
            return None

        return decode_from_cache(report_type, json.loads(cached_value))

    async def save_to_cache(
        self,
        user_id: int,
        version: str,
        parameters: dict,
        report: Any,
    ) -> None:
        await self._redis_client.set(
            self._key_for(user_id, version, parameters),
            json.dumps(encode_for_cache(report)),
            ex=int(CacheSettings.TTL_SECONDS),
        )

    def _key_for(self, user_id: int, version: str, parameters: dict) -> str:
        return get_analytics_cache_key(
            report_name=self._report_name,
            user_id=user_id,
            version=version,
            parameters_hash=get_parameters_hash(parameters),
        )


def _as_version(raw_version: str | None) -> int:
    return int(raw_version) if raw_version is not None else 0
