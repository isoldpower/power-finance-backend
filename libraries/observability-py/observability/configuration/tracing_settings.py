import os
from dataclasses import dataclass

ENVIRONMENT_VARIABLE_SERVICE_NAME = "OTEL_SERVICE_NAME"
ENVIRONMENT_VARIABLE_EXPORTER_ENDPOINT = "OTEL_EXPORTER_OTLP_ENDPOINT"
ENVIRONMENT_VARIABLE_SDK_DISABLED = "OTEL_SDK_DISABLED"
ENVIRONMENT_VARIABLE_SAMPLER_RATIO = "OTEL_TRACES_SAMPLER_ARG"
ENVIRONMENT_VARIABLE_DEPLOYMENT_ENVIRONMENT = "OTEL_DEPLOYMENT_ENVIRONMENT"

DEFAULT_EXPORTER_ENDPOINT = "http://localhost:4317"
DEFAULT_SAMPLER_RATIO = 1.0
DEFAULT_DEPLOYMENT_ENVIRONMENT = "development"

TRUE_LIKE_VALUES = frozenset({"1", "true", "yes", "on"})


@dataclass(frozen=True, slots=True)
class TracingSettings:
    service_name: str
    exporter_endpoint: str
    sampler_ratio: float
    deployment_environment: str
    is_enabled: bool


def resolve_tracing_settings(default_service_name: str) -> TracingSettings:
    return TracingSettings(
        service_name=os.environ.get(ENVIRONMENT_VARIABLE_SERVICE_NAME) or default_service_name,
        exporter_endpoint=os.environ.get(
            ENVIRONMENT_VARIABLE_EXPORTER_ENDPOINT,
            DEFAULT_EXPORTER_ENDPOINT,
        ),
        sampler_ratio=_resolve_sampler_ratio(),
        deployment_environment=os.environ.get(
            ENVIRONMENT_VARIABLE_DEPLOYMENT_ENVIRONMENT,
            DEFAULT_DEPLOYMENT_ENVIRONMENT,
        ),
        is_enabled=_resolve_is_enabled(),
    )


def _resolve_is_enabled() -> bool:
    if _is_true_like(os.environ.get(ENVIRONMENT_VARIABLE_SDK_DISABLED)):
        return False

    return bool(os.environ.get(ENVIRONMENT_VARIABLE_EXPORTER_ENDPOINT, "").strip())


def _resolve_sampler_ratio() -> float:
    raw_sampler_ratio = os.environ.get(ENVIRONMENT_VARIABLE_SAMPLER_RATIO)
    if not raw_sampler_ratio:
        return DEFAULT_SAMPLER_RATIO

    try:
        return float(raw_sampler_ratio)
    except ValueError:
        return DEFAULT_SAMPLER_RATIO


def _is_true_like(raw_value: str | None) -> bool:
    if not raw_value:
        return False

    return raw_value.strip().lower() in TRUE_LIKE_VALUES
