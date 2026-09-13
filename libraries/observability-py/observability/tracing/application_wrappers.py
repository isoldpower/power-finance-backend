from collections.abc import Callable
from typing import Any


def wrap_asgi_application(asgi_application: Any) -> Any:
    from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware

    return OpenTelemetryMiddleware(asgi_application)


def wrap_wsgi_application(wsgi_application: Callable[..., Any]) -> Callable[..., Any]:
    from opentelemetry.instrumentation.wsgi import OpenTelemetryMiddleware

    return OpenTelemetryMiddleware(wsgi_application)
