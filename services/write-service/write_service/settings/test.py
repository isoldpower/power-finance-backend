"""Test settings: SQLite in-memory DB, no external dependencies.

Health probe and unit tests are intentionally hermetic — they patch out the
real Postgres/ImmuDB/Redis/Kafka clients rather than connecting. Using
SQLite here keeps Django's test runner happy (it needs *some* working DB
to call `create_test_db`) without requiring a live Postgres in CI or local.
"""

from .base import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
