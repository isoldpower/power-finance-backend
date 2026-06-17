"""ASGI config for write_service: exposes the ASGI callable as a module-level
variable named ``application``."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "write_service.settings.local")

application = get_asgi_application()
