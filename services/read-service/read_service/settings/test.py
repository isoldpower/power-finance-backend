"""Test settings: Postgres test DB, external dependencies patched out.

Tests run against a real Postgres so the `data_read_core` migrations build the
test schema the same way production does. Django auto-creates and tears down
`test_<NAME>`.

Defaults point at the `postgres-read` container from the compose stack
(exposed on host port 5434); override via env for CI.
"""

import os

from .base import *  # noqa: F401,F403

TESTING = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("TEST_DATABASE_NAME", "power_finance_read"),
        "USER": os.environ.get("TEST_DATABASE_USER", "postgres"),
        "PASSWORD": os.environ.get("TEST_DATABASE_PASSWORD", "postgres"),
        "HOST": os.environ.get("TEST_DATABASE_HOST", "localhost"),
        "PORT": os.environ.get("TEST_DATABASE_PORT", "5434"),
        "CONN_MAX_AGE": 0,
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
