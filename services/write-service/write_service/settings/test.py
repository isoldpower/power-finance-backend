"""Test settings: Postgres test DB, ImmuDB/Redis/Kafka patched out.

Tests run against a real Postgres because the `data_write_core` migrations
include Postgres-only DDL (e.g. `DROP TABLE ... CASCADE` in 0003) and we
keep the migration set authoritative — the test schema must build the same
way production does. Django auto-creates and tears down `test_<NAME>`.

Defaults point at the `postgres-write` container from the compose stack
(exposed on host port 5433); override via env for CI.
"""

import os

from .base import *  # noqa: F401,F403

TESTING = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("TEST_DATABASE_NAME", "power_finance_write"),
        "USER": os.environ.get("TEST_DATABASE_USER", "postgres"),
        "PASSWORD": os.environ.get("TEST_DATABASE_PASSWORD", "postgres"),
        "HOST": os.environ.get("TEST_DATABASE_HOST", "localhost"),
        "PORT": os.environ.get("TEST_DATABASE_PORT", "5433"),
        "CONN_MAX_AGE": 0,
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
