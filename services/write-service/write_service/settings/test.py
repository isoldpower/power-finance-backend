"""Test settings: Postgres test DB, external dependencies patched out.

Tests run against a real Postgres so the `data_write_core` migrations build the
test schema the same way production does. Django auto-creates and tears down
`test_<NAME>`.

The ports below sit off the ones `make devhost-tunnels` forwards. On a tunnelled
laptop localhost:5433/5434/5436 are the DEV HOST's databases, and a test run
that reaches one of those creates and drops its test database on the machine
everyone shares. `make test-datastores` starts what these defaults expect.
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
        "PORT": os.environ.get("TEST_DATABASE_PORT", "5533"),
        "CONN_MAX_AGE": 0,
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
