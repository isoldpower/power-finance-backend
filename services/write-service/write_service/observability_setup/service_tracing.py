from observability import (
    DjangoInstrumentationActivator,
    PsycopgInstrumentationActivator,
    RedisInstrumentationActivator,
    configure_tracing,
)

DEFAULT_SERVICE_NAME = "write-service"


def configure_write_service_tracing() -> None:
    configure_tracing(
        default_service_name=DEFAULT_SERVICE_NAME,
        instrumentation_activators=(
            DjangoInstrumentationActivator(),
            PsycopgInstrumentationActivator(),
            RedisInstrumentationActivator(),
        ),
    )
