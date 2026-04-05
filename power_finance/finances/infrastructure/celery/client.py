import os

from celery import Celery
from django.utils import timezone


def build_celery_config(resolved_settings: dict) -> dict:
    return {
        "broker_url": resolved_settings.get('CELERY_BROKER_URL'),
        "result_backend": resolved_settings.get('CELERY_RESULT_BACKEND'),
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "result_accept_content": ["json"],
        "timezone": timezone.get_current_timezone_name(),
        "enable_utc": True,
        "task_track_started": True,
        "task_time_limit": 1800,
        "task_soft_time_limit": 1500,
        "beat_schedule": {
            "schedule-due-webhook-retries-every-10-seconds": {
                "task": "finances.schedule_due_webhook_retries",
                "schedule": 10.0,
            },
        },
    }

def build_celery_client(resolved_settings: dict) -> Celery:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "power_finance.settings")

    celery_instance = Celery(main=resolved_settings.get('APP_NAME'), strict_typing=True)
    celery_instance.conf.update(build_celery_config(resolved_settings))
    celery_instance.autodiscover_tasks(['finances.infrastructure.celery.tasks'])

    return celery_instance
