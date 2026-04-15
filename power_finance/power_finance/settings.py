import sys
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent
ENV_FILE = str(ROOT_DIR.joinpath('.env'))

# Define defaults for environment variables
env = environ.Env(
    APP_NAME=(str, 'power_finance'),
    DEBUG=(bool, True),
    DATABASE_HOST=(str, 'localhost'),
    DATABASE_PORT=(str, '5433'),
    DATABASE_USER=(str, 'postgres'),
    REDIS_HOST=(str, 'localhost'),
    REDIS_PORT=(str, '6380'),
    REDIS_PASSWORD=(str, ''),
    REDIS_CELERY_DATABASE_INDEX=(str, '2'),
    RABBIT_MQ_HOST=(str, 'localhost'),
    RABBIT_MQ_PORT=(str, '5673'),
    RABBIT_MQ_USER=(str, 'guest'),
    RABBIT_MQ_PASSWORD=(str, 'guest'),
    CLERK_CACHE_KEY=(str, 'clerk_cache'),
    API_VERSION=(str, 'v1'),
    CELERY_BEAT_SCHEDULE_FILENAME=(str, 'cache/celerybeat-schedule'),
)

env.read_env(ENV_FILE)

# List all environment variables
RESOLVED_ENV = {
    # Django core
    'APP_NAME': env('APP_NAME'),
    'DEBUG': env('DEBUG'),
    'SECRET_KEY': env('SECRET_KEY'),
    'API_VERSION': env('API_VERSION'),

    # Database
    'DATABASE_USER': env('DATABASE_USER'),
    'DATABASE_PASSWORD': env('DATABASE_PASSWORD'),
    'DATABASE_HOST': env('DATABASE_HOST'),
    'DATABASE_PORT': env('DATABASE_PORT'),

    # Redis
    'REDIS_HOST': env('REDIS_HOST'),
    'REDIS_PORT': env('REDIS_PORT'),
    'REDIS_PASSWORD': env('REDIS_PASSWORD'),
    'REDIS_CELERY_DATABASE_INDEX': env('REDIS_CELERY_DATABASE_INDEX'),

    # RabbitMQ
    'RABBIT_MQ_HOST': env('RABBIT_MQ_HOST'),
    'RABBIT_MQ_PORT': env('RABBIT_MQ_PORT'),
    'RABBIT_MQ_USER': env('RABBIT_MQ_USER'),
    'RABBIT_MQ_PASSWORD': env('RABBIT_MQ_PASSWORD'),

    # Clerk
    'CLERK_SECRET_KEY': env('CLERK_SECRET_KEY'),
    'CLERK_API_URL': env('CLERK_API_URL'),
    'CLERK_CACHE_KEY': env('CLERK_CACHE_KEY'),

    # Celery
    'CELERY_BEAT_SCHEDULE_FILENAME': str(ROOT_DIR.joinpath(env('CELERY_BEAT_SCHEDULE_FILENAME'))),
}

# Project configuration settings
SECRET_KEY = RESOLVED_ENV['SECRET_KEY']
DEBUG = RESOLVED_ENV['DEBUG']
ALLOWED_HOSTS = ['*']

# Detect if we are running in a Celery process (worker or beat)
IS_CELERY_PROCESS = any(arg in sys.argv for arg in ['celery', 'worker', 'beat'])
LOGS_DIR = ROOT_DIR / 'logs'
LOGS_DIR.mkdir(parents=True, exist_ok=True)  # Create logs dir if it doesn't exist

CACHE_DIR = ROOT_DIR / 'cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)  # Create cache dir if it doesn't exist

DEBUG_LOG_PATH = str(LOGS_DIR / 'debug.log')
CELERY_LOG_PATH = str(LOGS_DIR / 'celery-debug.log')

# If it's a celery process, everything goes to celery-debug.log
MAIN_FILE_PATH = CELERY_LOG_PATH if IS_CELERY_PROCESS else DEBUG_LOG_PATH

CELERY_BEAT_SCHEDULE_FILENAME = RESOLVED_ENV['CELERY_BEAT_SCHEDULE_FILENAME']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': { 'format': '{levelname} {asctime} {module} {message}', 'style': '{' },
    },
    'handlers': {
        'console': {'level': 'DEBUG', 'class': 'logging.StreamHandler', 'formatter': 'verbose'},
        'file': {
            'level': 'INFO', 
            'class': 'logging.FileHandler', 
            'filename': MAIN_FILE_PATH, 
            'formatter': 'verbose',
            'delay': True
        },
    },
    'loggers': {
        '': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': True},
        RESOLVED_ENV['APP_NAME']: {'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': False},
        'finances': {'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': False},
        'identity': {'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': False},
        'celery': {'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': False},
    },
}

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'rest_framework',
    'drf_spectacular',

    'power_finance',
    'environment.apps.EnvironmentConfig',
    'finances.apps.FinancesConfig',
]

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'environment.authentication.ClerkJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'environment.presentation.middleware.AnonRedisThrottle',
        'environment.presentation.middleware.UserRedisThrottle',
        'environment.presentation.middleware.WriteThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/min',
        'user': '200/min',
        'writes': '60/min',
        'analytics': '30/min',
        'webhook_registration': '10/hour',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Power Finance API',
    'DESCRIPTION': 'API documentation for Power Finance',
    'VERSION': '1.0.0',
    'SCHEMA_PATH_PREFIX': r'/api/v[0-9]+/',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': """{
        deepLinking: true,
        urls: [{url: '/api/schema/', name: 'v1'}],
        layout: 'StandaloneLayout',
        presets: [
            SwaggerUIBundle.presets.apis,
            SwaggerUIStandalonePreset
        ],
    }""",
    'APPEND_COMPONENTS': {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
    },
    'SECURITY': [{"bearerAuth": []}]
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
]
CORS_ALLOW_CREDENTIALS = True
ROOT_URLCONF = 'power_finance.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'power_finance.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': RESOLVED_ENV['DATABASE_USER'],
        'USER': RESOLVED_ENV['DATABASE_USER'],
        'PASSWORD': RESOLVED_ENV['DATABASE_PASSWORD'],
        'HOST': RESOLVED_ENV['DATABASE_HOST'],
        'PORT': RESOLVED_ENV['DATABASE_PORT'],
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'pool': True
        }
    }
}

CONN_MAX_AGE = 0

MIGRATION_MODULES = {
    "finances": "finances.infrastructure.orm.migrations",
    "identity": "identity.infrastructure.orm.migrations"
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
