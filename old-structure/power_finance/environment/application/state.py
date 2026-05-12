from dataclasses import dataclass

from pika.connection import ConnectionParameters
from redis.asyncio.client import Redis
from redis import Redis as SyncRedis


@dataclass(frozen=True)
class ApplicationState:
    redis: Redis
    sync_redis: SyncRedis
    rabbit_mq_connection: ConnectionParameters
    initialized: bool = False


@dataclass(frozen=True)
class ApplicationEnvironment:
    redis_host: str
    redis_port: int
    redis_password: str
    redis_default_db_index: int
    rabbitmq_host: str
    rabbitmq_port: int
    rabbitmq_username: str
    rabbitmq_password: str
