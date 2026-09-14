import os

from .base import *  # noqa: F401,F403

TESTING = True

# Ports sit off the ones `make sandbox-tunnels` forwards. On a tunnelled laptop
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
