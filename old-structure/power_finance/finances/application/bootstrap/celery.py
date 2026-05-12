from celery import Celery

from .state import ApplicationEnvironment

from finances.infrastructure.celery import build_celery_client


def initialize_celery(environment: ApplicationEnvironment) -> Celery:
    return build_celery_client(
        app_name=environment.app_name,
        rmq_host=environment.rabbitmq_host,
        rmq_port=environment.rabbitmq_port,
        rmq_user=environment.rabbitmq_user,
        rmq_password=environment.rabbitmq_password,
        redis_host=environment.redis_host,
        redis_port=environment.redis_port,
        redis_password=environment.redis_password,
        redis_celery_db=environment.redis_celery_db_index,
        beat_schedule_filename=environment.celery_beat_filename,
    )