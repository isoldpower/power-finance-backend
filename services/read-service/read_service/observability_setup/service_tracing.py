from observability import (
    DjangoInstrumentationActivator,
    ElasticsearchInstrumentationActivator,
    PsycopgInstrumentationActivator,
    RedisInstrumentationActivator,
    configure_tracing,
)

DEFAULT_SERVICE_NAME = "read-service"


def configure_read_service_tracing() -> None:
    configure_tracing(
        default_service_name=DEFAULT_SERVICE_NAME,
        instrumentation_activators=(
            DjangoInstrumentationActivator(),
            PsycopgInstrumentationActivator(),
            RedisInstrumentationActivator(),
            ElasticsearchInstrumentationActivator(),
        ),
    )
