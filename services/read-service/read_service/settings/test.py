"""Test settings: Postgres test DB, external dependencies patched out.

Tests run against a real Postgres so the `data_read_core` migrations build the
test schema the same way production does. Django auto-creates and tears down
`test_<NAME>`.

`ELASTICSEARCH_INDEX_PREFIX` is cleared because index names are built from it at
import time, so a shell that has sourced a sandbox env file would otherwise
point the suite at that sandbox's indices — `sbx_<name>_read_transactions`
rather than `read_transactions`.

The ports below sit off the ones `make devhost-tunnels` forwards, for the same
reason: on a tunnelled laptop localhost:5433/5434/5436 are the DEV HOST's
databases, and a test run that reaches one of those creates and drops its test
database on the machine everyone shares. A test run must not be able to reach
shared infrastructure just because of what the surrounding shell happens to
export. `make test-datastores` starts what these defaults expect.
"""

import os

from .base import *  # noqa: F401,F403

TESTING = True

os.environ["ELASTICSEARCH_INDEX_PREFIX"] = ""


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("TEST_DATABASE_NAME", "power_finance_read"),
        "USER": os.environ.get("TEST_DATABASE_USER", "postgres"),
        "PASSWORD": os.environ.get("TEST_DATABASE_PASSWORD", "postgres"),
        "HOST": os.environ.get("TEST_DATABASE_HOST", "localhost"),
        "PORT": os.environ.get("TEST_DATABASE_PORT", "5534"),
        "CONN_MAX_AGE": 0,
    }
}

EXCHANGE_RATES = {
    **EXCHANGE_RATES,  # noqa: F405
    "PROVIDER": "static",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
