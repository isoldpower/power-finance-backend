from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

# Define defaults for environment variables
env = environ.Env(
    DEBUG=(bool, True),
    DATABASE_PORT=(str, '5433'),
    DATABASE_USER=(str, 'postgres')
)
env.read_env(str(ROOT_DIR.joinpath('.env')))

# List all environment variables
RESOLVED_ENV = {
    'DEBUG': env('DEBUG'),
    'DATABASE_PASSWORD': env('DATABASE_PASSWORD'),
    'DATABASE_PORT': env('DATABASE_PORT'),
    'DATABASE_USER': env('DATABASE_USER'),
    'SECRET_KEY': env('SECRET_KEY')
}

# Project configuration settings
SECRET_KEY = RESOLVED_ENV['SECRET_KEY']
DEBUG = RESOLVED_ENV['DEBUG']
ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'finance_backend.urls'

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

WSGI_APPLICATION = 'finance_backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': RESOLVED_ENV['DATABASE_USER'],
        'USER': RESOLVED_ENV['DATABASE_USER'],
        'PASSWORD': RESOLVED_ENV['DATABASE_PASSWORD'],
        'HOST': 'localhost',
        'PORT': RESOLVED_ENV['DATABASE_PORT'],
        'OPTIONS': {
            'pool': True
        }
    }
}
CONN_MAX_AGE = 0


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
