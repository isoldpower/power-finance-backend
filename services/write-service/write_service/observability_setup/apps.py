from django.apps import AppConfig


class WriteServiceObservabilityConfig(AppConfig):
    name = "write_service.observability_setup"
    label = "write_service_observability"

    def ready(self) -> None:
        from .service_tracing import configure_write_service_tracing

        configure_write_service_tracing()
