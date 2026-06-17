"""Test settings: a real Postgres test DB (migrations include Postgres-only DDL),
with ImmuDB/Redis/Kafka patched out."""

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
