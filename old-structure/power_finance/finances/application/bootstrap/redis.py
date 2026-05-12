from .state import RedisClient, ApplicationEnvironment

from finances.infrastructure.redis import build_redis_client, build_sync_redis_client


def initialize_redis(environment: ApplicationEnvironment) -> RedisClient:
    return RedisClient(
        async_client=build_redis_client(
            host=environment.redis_host,
            port=environment.redis_port,
            password=environment.redis_password,
            db=environment.redis_default_db_index,
        ),
        sync_client=build_sync_redis_client(
            host=environment.redis_host,
            port=environment.redis_port,
            password=environment.redis_password,
            db=environment.redis_default_db_index,
        )
    )
