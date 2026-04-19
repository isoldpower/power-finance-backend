from pika.connection import ConnectionParameters
from redis.asyncio.client import Redis
from redis import Redis as SyncRedis

from .state import ApplicationState, ApplicationEnvironment

from environment.infrastructure.redis import build_redis_client, build_sync_redis_client
from environment.infrastructure.rabbitmq import build_rabbitmq_connection


application: ApplicationState | None = None

def bootstrap_application(environment: ApplicationEnvironment):
    global application

    if application:
        return

    application = ApplicationState(
        initialized=True,
        redis=build_redis_client(
            host=environment.redis_host,
            port=environment.redis_port,
            password=environment.redis_password,
            db=environment.redis_default_db_index,
        ),
        sync_redis=build_sync_redis_client(
            host=environment.redis_host,
            port=environment.redis_port,
            password=environment.redis_password,
            db=environment.redis_default_db_index,
        ),
        rabbit_mq_connection=build_rabbitmq_connection(
            host=environment.rabbitmq_host,
            port=environment.rabbitmq_port,
            username=environment.rabbitmq_username,
            password=environment.rabbitmq_password,
        )
    )

def get_redis_client(sync: bool = True) -> Redis | SyncRedis:
    if application is None or not application.initialized:
        raise RuntimeError("Application is not bootstrapped or still initializing")

    return application.sync_redis if sync else application.redis

def get_rabbitmq_connection() -> ConnectionParameters:
    if application is None or not application.initialized:
        raise RuntimeError("Application is not bootstrapped or still initializing")

    return application.rabbit_mq_connection
