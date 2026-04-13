from redis import Redis


def build_redis_client(host: str, port: str, password: str, db: int = 0) -> Redis:
    url = f"redis://:{password}@{host}:{port}/{db}"
    return Redis.from_url(url, decode_responses=True)
