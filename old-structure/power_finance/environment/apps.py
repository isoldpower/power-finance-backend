from django.apps import AppConfig
from django.conf import settings



class EnvironmentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'environment'

    def ready(self) -> None:
        import environment.presentation.spectacular_extensions
        from .application.bootstrap import bootstrap_application
        from .application.state import ApplicationEnvironment

        environment = ApplicationEnvironment(
            redis_host=settings.RESOLVED_ENV['REDIS_HOST'],
            redis_port=settings.RESOLVED_ENV['REDIS_PORT'],
            redis_password=settings.RESOLVED_ENV['REDIS_PASSWORD'],
            redis_default_db_index=0,
            rabbitmq_host=settings.RESOLVED_ENV['RABBIT_MQ_HOST'],
            rabbitmq_port=settings.RESOLVED_ENV['RABBIT_MQ_PORT'],
            rabbitmq_username=settings.RESOLVED_ENV['RABBIT_MQ_USER'],
            rabbitmq_password=settings.RESOLVED_ENV['RABBIT_MQ_PASSWORD'],
        )
        bootstrap_application(environment)
