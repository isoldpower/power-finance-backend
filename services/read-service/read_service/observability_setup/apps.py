from django.apps import AppConfig


class ReadServiceObservabilityConfig(AppConfig):
    name = "read_service.observability_setup"
    label = "read_service_observability"

    def ready(self) -> None:
        from .service_tracing import configure_read_service_tracing

        configure_read_service_tracing()
