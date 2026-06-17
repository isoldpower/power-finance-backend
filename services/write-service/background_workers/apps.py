from django.apps import AppConfig


class BackgroundWorkersConfig(AppConfig):
    """Kafka consumer entrypoints for the write side, currently the inbound
    notifications worker that persists requested notifications."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "background_workers"
    label = "write_background_workers"
