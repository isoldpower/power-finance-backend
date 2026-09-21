from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import (
    DEPLOYMENT_ENVIRONMENT,
    SERVICE_NAME,
    Resource,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_ON,
    ParentBased,
    Sampler,
    TraceIdRatioBased,
)

from ..configuration import TracingSettings

FULL_SAMPLING_RATIO = 1.0


def build_tracer_provider(settings: TracingSettings) -> TracerProvider:
    tracer_provider = TracerProvider(
        resource=_build_resource(settings),
        sampler=_build_sampler(settings.sampler_ratio),
    )
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.exporter_endpoint,
                insecure=True,
            )
        ),
    )

    return tracer_provider


def install_tracer_provider(tracer_provider: TracerProvider) -> None:
    trace.set_tracer_provider(tracer_provider)


def _build_resource(settings: TracingSettings) -> Resource:
    return Resource.create(
        {
            SERVICE_NAME: settings.service_name,
            DEPLOYMENT_ENVIRONMENT: settings.deployment_environment,
        },
    )


def _build_sampler(sampler_ratio: float) -> Sampler:
    if sampler_ratio >= FULL_SAMPLING_RATIO:
        return ParentBased(ALWAYS_ON)

    return ParentBased(TraceIdRatioBased(sampler_ratio))
