"""Base settings shared by all environments. Concrete environments (local,
production) extend this module and override values that differ.

Environment variables are loaded via django-environ from a `.env` file at
the service root. See `.env.example` for the full list of recognised keys.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
    DATABASE_HOST=(str, "localhost"),
    DATABASE_PORT=(str, "5432"),
    DATABASE_NAME=(str, "power_finance_read"),
    DATABASE_USER=(str, "postgres"),
    DATABASE_PASSWORD=(str, "postgres"),
    KAFKA_BOOTSTRAP_SERVERS=(str, "localhost:9092"),
    KAFKA_OUTBOX_TOPIC=(str, "events.async"),
    KAFKA_READ_GROUP_ID=(str, "read-service.test-consumer"),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    LOG_LEVEL=(str, "INFO"),
)
if ENV_FILE.exists():
    env.read_env(str(ENV_FILE))

SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-x@l4to$=9hnh^4(0@z%ip!b*t-w7bbnwx&af(a#k&59+_mel!1",
)
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

ROOT_URLCONF = "read_service.urls"
WSGI_APPLICATION = "read_service.wsgi.application"
ASGI_APPLICATION = "read_service.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "data_read_core",
    "background_workers",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Read store — a separate Postgres instance from the write service's,
# holding only denormalised projections built from the event stream.
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
            },
        },
    }
}

# Redis — backing store for read-side caches (single-wallet entries, etc.).
# Used by the cache-eviction effects in the Kafka consumer. Sourced from the
# environment; the default targets a local Redis.
REDIS_URL = env("REDIS_URL")

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "data_read_core.shared.user_auth.GatewayUserHeaderAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "data_read_core.shared.user_auth.IsGatewayAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Kafka consumer configuration. Read by the background_workers Kafka consumers
# (e.g. the run_write_message_consumer management command). Sourced from the
# environment so each deployment sets it via compose; the defaults target a
# local broker.
KAFKA = {
    "BOOTSTRAP_SERVERS": env("KAFKA_BOOTSTRAP_SERVERS"),
    "OUTBOX_TOPIC": env("KAFKA_OUTBOX_TOPIC"),
    "READ_GROUP_ID": env("KAFKA_READ_GROUP_ID"),
}

# Logging. Django leaves the root logger at WARNING by default, which hides
# INFO from the background_workers consumers. Route app + consumer logs to the
# console at LOG_LEVEL so projection activity is visible in `docker logs`.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "loggers": {
        "background_workers": {
            "handlers": ["console"],
            "level": env("LOG_LEVEL"),
            "propagate": False,
        },
        "data_read_core": {"handlers": ["console"], "level": env("LOG_LEVEL"), "propagate": False},
        "query_slices": {"handlers": ["console"], "level": env("LOG_LEVEL"), "propagate": False},
    },
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
