import os
import sys
from pathlib import Path

# Add the project root to sys.path so that 'finances' can be found.
# This assumes this file is in power_finance/power_finance/celery.py
# and the modules like 'finances' are in power_finance/
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from django.conf import settings
from finances.infrastructure.celery.client import build_celery_client

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'power_finance.settings')

app = build_celery_client(
    app_name=settings.RESOLVED_ENV['APP_NAME'],
    rmq_host=settings.RESOLVED_ENV['RABBIT_MQ_HOST'],
    rmq_port=settings.RESOLVED_ENV['RABBIT_MQ_PORT'],
    rmq_user=settings.RESOLVED_ENV['RABBIT_MQ_USER'],
    rmq_password=settings.RESOLVED_ENV['RABBIT_MQ_PASSWORD'],
    redis_host=settings.RESOLVED_ENV['REDIS_HOST'],
    redis_port=settings.RESOLVED_ENV['REDIS_PORT'],
    redis_password=settings.RESOLVED_ENV['REDIS_PASSWORD'],
    redis_celery_db=settings.RESOLVED_ENV['REDIS_CELERY_DATABASE_INDEX'],
    beat_schedule_filename=settings.RESOLVED_ENV['CELERY_BEAT_SCHEDULE_FILENAME'],
)
