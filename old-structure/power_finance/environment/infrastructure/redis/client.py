from redis import Redis as SyncRedis
from redis.asyncio.client import Redis


def _build_redis_url(host: str, port: int, password: str, db: int = 0):
    return f"redis://:{password}@{host}:{port}/{db}"


def build_redis_client(host: str, port: int, password: str, db: int = 0) -> Redis:
    return Redis.from_url(
        url=_build_redis_url(host, port, password, db),
        decode_responses=True,
    )


def build_sync_redis_client(host: str, port: int, password: str, db: int = 0) -> SyncRedis:
    return SyncRedis.from_url(
        url=_build_redis_url(host, port, password, db),
        decode_responses=True,
    )
