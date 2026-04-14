from redis.asyncio.client import Redis
from redis import Redis as SyncRedis


def build_redis_client(host: str, port: int, password: str, db: int = 0) -> Redis:
    url = f"redis://:{password}@{host}:{port}/{db}"
    return Redis.from_url(url, decode_responses=True)

def build_sync_redis_client(host: str, port: int, password: str, db: int = 0) -> SyncRedis:
    url = f"redis://:{password}@{host}:{port}/{db}"
    return SyncRedis.from_url(url, decode_responses=True)
