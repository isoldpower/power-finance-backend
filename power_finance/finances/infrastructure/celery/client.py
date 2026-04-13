import os

from celery import Celery
from django.utils import timezone
from pika import ConnectionParameters, PlainCredentials


def _build_amqp_url(host: str, port: str, user: str, password: str) -> str:
    params = ConnectionParameters(
        host=host,
        port=int(port),
        credentials=PlainCredentials(username=user, password=password),
    )
    return (
        f"amqp://{params.credentials.username}:{params.credentials.password}"
        f"@{params.host}:{params.port}//"
    )


def _build_redis_url(host: str, port: str, password: str, db: str) -> str:
    return f"redis://:{password}@{host}:{port}/{db}"


def build_celery_config(
        rmq_host: str,
        rmq_port: str,
        rmq_user: str,
        rmq_password: str,
        redis_host: str,
        redis_port: str,
        redis_password: str,
        redis_celery_db: str,
        beat_schedule_filename: str,
) -> dict:
    return {
        "broker_url": _build_amqp_url(
            host=rmq_host,
            port=rmq_port,
            user=rmq_user,
            password=rmq_password,
        ),
        "result_backend": _build_redis_url(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            db=redis_celery_db,
        ),
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "result_accept_content": ["json"],
        "timezone": timezone.get_current_timezone_name(),
        "enable_utc": True,
        "task_track_started": True,
        "task_time_limit": 1800,
        "task_soft_time_limit": 1500,
        "beat_schedule_filename": beat_schedule_filename,
        "beat_schedule": {
            "schedule-due-webhook-retries-every-10-seconds": {
                "task": "finances.schedule_due_webhook_retries",
                "schedule": 10.0,
            },
        },
    }


def build_celery_client(
        app_name: str,
        rmq_host: str,
        rmq_port: str,
        rmq_user: str,
        rmq_password: str,
        redis_host: str,
        redis_port: str,
        redis_password: str,
        redis_celery_db: str,
        beat_schedule_filename: str,
) -> Celery:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "power_finance.settings")

    celery_instance = Celery(main=app_name, strict_typing=True)
    celery_instance.conf.update(build_celery_config(
        rmq_host=rmq_host,
        rmq_port=rmq_port,
        rmq_user=rmq_user,
        rmq_password=rmq_password,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password,
        redis_celery_db=redis_celery_db,
        beat_schedule_filename=beat_schedule_filename,
    ))
    celery_instance.autodiscover_tasks(['finances.infrastructure.celery.tasks'])

    return celery_instance
