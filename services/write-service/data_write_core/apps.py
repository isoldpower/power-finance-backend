from django.apps import AppConfig


class DataWriteCoreConfig(AppConfig):
    """Single Django app holding all write-side business logic and
    cross-cutting infrastructure: domain aggregates (accounts, finances),
    the transactional outbox, the ImmuDB SAGA adapter, and the Fraud Redis
    fast-path client. Will be split into multiple apps if/when the surface
    area justifies it."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "data_write_core"
    label = "data_write_core"
