import os

from django.core.wsgi import get_wsgi_application
from observability import wrap_wsgi_application

from ..observability_setup import configure_write_service_tracing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "write_service.settings.local")

configure_write_service_tracing()

application = wrap_wsgi_application(get_wsgi_application())
