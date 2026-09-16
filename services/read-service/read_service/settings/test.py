import os

from .base import *  # noqa: F401,F403

TESTING = True

# Index names are built from this at import time, so a shell that has sourced a
# sandbox env file would otherwise point the suite at that sandbox's indices —
# `sbx_<name>_read_transactions` rather than `read_transactions`. The same reasoning
# as the ports below: a test run must not be able to reach shared infrastructure
# just because of what the surrounding shell happens to export.
os.environ["ELASTICSEARCH_INDEX_PREFIX"] = ""

# Ports sit off the ones `make devhost-tunnels` forwards. On a tunnelled laptop
# localhost:5433/5434/5436 are the DEV HOST's databases, and a test run that reaches
# one of those creates and drops its test database on the machine everyone shares.
# `make test-datastores` starts what these defaults expect.

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
