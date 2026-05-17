from django.apps import AppConfig
from django.conf import settings


class DataWriteCoreConfig(AppConfig):
    """Single Django app holding all write-side business logic and
    cross-cutting infrastructure: domain aggregates (accounts, finances),
    the transactional outbox, the ImmuDB SAGA adapter, and the Fraud Redis
    fast-path client. Will be split into multiple apps if/when the surface
    area justifies it."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "data_write_core"
    label = "data_write_core"

    def ready(self) -> None:
        from data_write_core.application.bootstrap import (
            ApplicationEnvironment,
            bootstrap_application,
        )

        bootstrap_application(
            ApplicationEnvironment(
                immudb_host=settings.IMMUDB["HOST"],
                immudb_port=settings.IMMUDB["PORT"],
                immudb_user=settings.IMMUDB["USER"],
                immudb_password=settings.IMMUDB["PASSWORD"],
            )
        )
