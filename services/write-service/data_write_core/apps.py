from django.apps import AppConfig
from django.conf import settings


class DataWriteCoreConfig(AppConfig):
    """Single Django app holding all write-side business logic and
    cross-cutting infrastructure (outbox, SAGA adapter, fraud client)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "data_write_core"
    label = "data_write_core"

    def ready(self) -> None:
        from data_write_core.application.bootstrap import (
            ApplicationEnvironment,
            bootstrap_application,
        )
        from data_write_core.presentation.http.auth import schema  # noqa: F401

        bootstrap_application(
            ApplicationEnvironment(
                immudb_host=settings.IMMUDB["HOST"],
                immudb_port=settings.IMMUDB["PORT"],
                immudb_user=settings.IMMUDB["USER"],
                immudb_password=settings.IMMUDB["PASSWORD"],
            )
        )
