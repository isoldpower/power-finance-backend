"""Base settings shared by all environments. Concrete environments (local,
production) extend this module and override values that differ.

Environment variables are loaded via django-environ from a `.env` file at
the service root. See `.env.example` for the full list of recognised keys.
"""

from pathlib import Path

import environ
from psycopg_pool import ConnectionPool

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

env = environ.Env(
    DEBUG=(bool, False),
    APP_NAME=(str, "write_service"),
    API_VERSION=(str, "v1"),
    ALLOWED_HOSTS=(list, ["*"]),
    CORS_ALLOWED_ORIGINS=(list, []),
    DATABASE_HOST=(str, "localhost"),
    DATABASE_PORT=(str, "5432"),
    DATABASE_USER=(str, "postgres"),
    DATABASE_PASSWORD=(str, "postgres"),
    DATABASE_NAME=(str, "power_finance_write"),
    REDIS_HOST=(str, "localhost"),
    REDIS_PORT=(int, 6379),
    REDIS_PASSWORD=(str, ""),
    IDEMPOTENCY_REDIS_DB=(int, 0),
    IDEMPOTENCY_LOCK_TTL_SECONDS=(int, 30),
    IDEMPOTENCY_RESPONSE_TTL_SECONDS=(int, 86400),
    IMMUDB_HOST=(str, "localhost"),
    IMMUDB_PORT=(int, 3322),
    IMMUDB_USER=(str, "immudb"),
    IMMUDB_PASSWORD=(str, "immudb"),
    KAFKA_BOOTSTRAP_SERVERS=(str, "localhost:9092"),
    KAFKA_OUTBOX_TOPIC=(str, "events.async"),
    KAFKA_FRAUD_SIGNALS_TOPIC=(str, "fraud.signals"),
    CORRELATION_ID_HEADER=(str, "X-Correlation-ID"),
)
if ENV_FILE.exists():
    env.read_env(str(ENV_FILE))

SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
APP_NAME = env("APP_NAME")
API_VERSION = env("API_VERSION")

ROOT_URLCONF = "write_service.urls"
WSGI_APPLICATION = "write_service.wsgi.application"
ASGI_APPLICATION = "write_service.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "health_probes.apps.HealthProbesConfig",
    "data_write_core.apps.DataWriteCoreConfig",
    "write_service.common.apps.WriteServiceCommonConfig",
]

MIGRATION_MODULES = {
    "data_write_core": "data_write_core.infrastructure.orm.migrations",
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "correlation.CorrelationIDMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DATABASE_NAME"),
        "USER": env("DATABASE_USER"),
        "PASSWORD": env("DATABASE_PASSWORD"),
        "HOST": env("DATABASE_HOST"),
        "PORT": env("DATABASE_PORT"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "pool": {
                "min_size": 2,
                "max_size": 10,
                # Liveness probe (SELECT 1) on checkout so a Postgres
                # restart doesn't poison the pool with dead connections.
                "check": ConnectionPool.check_connection,
            },
        },
    }
}

REDIS = {
    "HOST": env("REDIS_HOST"),
    "PORT": env("REDIS_PORT"),
    "PASSWORD": env("REDIS_PASSWORD"),
}

IDEMPOTENCY = {
    "REDIS_DB": env("IDEMPOTENCY_REDIS_DB"),
    # In-flight lock TTL — bounds how long a stuck/crashed handler can hold
    # a key before another request is allowed through. Must comfortably
    # exceed worst-case request latency (SAGA + ImmuDB + outbox).
    "LOCK_TTL_SECONDS": env("IDEMPOTENCY_LOCK_TTL_SECONDS"),
    # Cached-response TTL after success. 24h matches the Stripe convention
    # — long enough for offline-client retries, short enough that key reuse
    # past a day processes again as a fresh request.
    "RESPONSE_TTL_SECONDS": env("IDEMPOTENCY_RESPONSE_TTL_SECONDS"),
}

IMMUDB = {
    "HOST": env("IMMUDB_HOST"),
    "PORT": env("IMMUDB_PORT"),
    "USER": env("IMMUDB_USER"),
    "PASSWORD": env("IMMUDB_PASSWORD"),
}

KAFKA = {
    "BOOTSTRAP_SERVERS": env("KAFKA_BOOTSTRAP_SERVERS"),
    "OUTBOX_TOPIC": env("KAFKA_OUTBOX_TOPIC"),
    "FRAUD_SIGNALS_TOPIC": env("KAFKA_FRAUD_SIGNALS_TOPIC"),
}

CORRELATION_ID_HEADER = env("CORRELATION_ID_HEADER")

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "data_write_core.infrastructure.auth.GatewayUserHeaderAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Power Finance — Write Service API",
    "DESCRIPTION": "Command side of the CQRS architecture. Synchronous, consistency-oriented writes.",
    "VERSION": "0.1.0",
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+/",
    "SERVE_INCLUDE_SCHEMA": False,
}

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "correlation_id": {"()": "correlation.CorrelationIDFilter"},
    },
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} cid={correlation_id} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["correlation_id"],
        },
    },
    "loggers": {
        "": {"handlers": ["console"], "level": "INFO", "propagate": True},
        "write_service": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
        "apps": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
