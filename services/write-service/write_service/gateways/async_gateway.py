import os

from django.core.asgi import get_asgi_application
from observability import wrap_asgi_application

from ..observability_setup import configure_write_service_tracing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "write_service.settings.local")

configure_write_service_tracing()

application = wrap_asgi_application(get_asgi_application())
