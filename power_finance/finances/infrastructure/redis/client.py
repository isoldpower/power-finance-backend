from redis import Redis


def build_redis_client(url: str) -> Redis:
    return Redis.from_url(url, decode_responses=True)