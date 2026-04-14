from django.apps import AppConfig
from django.conf import settings


class FinancesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finances'

    def ready(self) -> None:
        from finances.application.bootstrap import bootstrap_application, ApplicationEnvironment

        bootstrap_application(ApplicationEnvironment(
            app_name=settings.RESOLVED_ENV['APP_NAME'],
            rabbitmq_host=settings.RESOLVED_ENV['RABBIT_MQ_HOST'],
            rabbitmq_port=settings.RESOLVED_ENV['RABBIT_MQ_PORT'],
            rabbitmq_user=settings.RESOLVED_ENV['RABBIT_MQ_USER'],
            rabbitmq_password=settings.RESOLVED_ENV['RABBIT_MQ_PASSWORD'],
            redis_host=settings.RESOLVED_ENV['REDIS_HOST'],
            redis_port=settings.RESOLVED_ENV['REDIS_PORT'],
            redis_password=settings.RESOLVED_ENV['REDIS_PASSWORD'],
            redis_default_db_index=0,
            redis_celery_db_index=settings.RESOLVED_ENV['REDIS_CELERY_DATABASE_INDEX'],
            celery_beat_filename=settings.RESOLVED_ENV['CELERY_BEAT_SCHEDULE_FILENAME'],
        ))
