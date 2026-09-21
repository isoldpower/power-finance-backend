from django.apps import AppConfig


class DataReadCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "data_read_core"

    def ready(self) -> None:
        from .shared.user_auth import schema  # noqa: F401
