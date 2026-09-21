from observability import (
    FastapiInstrumentationActivator,
    PsycopgInstrumentationActivator,
    SqlalchemyInstrumentationActivator,
    configure_tracing,
)

DEFAULT_API_SERVICE_NAME = "ai-service"
DEFAULT_WORKER_SERVICE_NAME = "ai-dispatcher"


def configure_api_tracing() -> None:
    configure_tracing(
        default_service_name=DEFAULT_API_SERVICE_NAME,
        instrumentation_activators=(
            FastapiInstrumentationActivator(),
            SqlalchemyInstrumentationActivator(),
            PsycopgInstrumentationActivator(),
        ),
    )


def configure_worker_tracing() -> None:
    configure_tracing(
        default_service_name=DEFAULT_WORKER_SERVICE_NAME,
        instrumentation_activators=(
            SqlalchemyInstrumentationActivator(),
            PsycopgInstrumentationActivator(),
        ),
    )
