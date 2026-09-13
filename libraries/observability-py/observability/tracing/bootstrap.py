from collections.abc import Sequence

from ..configuration import TracingSettings, resolve_tracing_settings
from ..logging import get_observability_logger
from .instrumentation_registry import InstrumentationActivator, InstrumentationRegistry
from .tracer_provider_factory import build_tracer_provider, install_tracer_provider

_is_tracing_configured = False


def configure_tracing(
    *,
    default_service_name: str,
    instrumentation_activators: Sequence[InstrumentationActivator] = (),
) -> TracingSettings:
    global _is_tracing_configured

    settings = resolve_tracing_settings(default_service_name)
    logger = get_observability_logger()

    if _is_tracing_configured:
        return settings
    if not settings.is_enabled:
        logger.info("tracing disabled by environment, skipping tracer provider install")
        _is_tracing_configured = True
        return settings

    install_tracer_provider(build_tracer_provider(settings))

    registry = InstrumentationRegistry()
    for activator in instrumentation_activators:
        registry.register(activator)
    registry.activate_all()

    _is_tracing_configured = True
    logger.info(
        "tracing configured (service=%s endpoint=%s instrumentation=%s)",
        settings.service_name,
        settings.exporter_endpoint,
        registry.activated_instrumentation_names(),
    )

    return settings
