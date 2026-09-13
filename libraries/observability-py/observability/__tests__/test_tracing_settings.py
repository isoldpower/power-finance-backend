"""Tracing settings come from OTEL_* environment variables."""

from observability import resolve_tracing_settings
from observability.configuration.tracing_settings import (
    DEFAULT_EXPORTER_ENDPOINT,
    ENVIRONMENT_VARIABLE_EXPORTER_ENDPOINT,
    ENVIRONMENT_VARIABLE_SAMPLER_RATIO,
    ENVIRONMENT_VARIABLE_SDK_DISABLED,
    ENVIRONMENT_VARIABLE_SERVICE_NAME,
)

DEFAULT_SERVICE_NAME_FOR_TESTS = "write-service"


def test_defaults_apply_without_environment(monkeypatch):
    for variable_name in (
        ENVIRONMENT_VARIABLE_SERVICE_NAME,
        ENVIRONMENT_VARIABLE_EXPORTER_ENDPOINT,
        ENVIRONMENT_VARIABLE_SDK_DISABLED,
        ENVIRONMENT_VARIABLE_SAMPLER_RATIO,
    ):
        monkeypatch.delenv(variable_name, raising=False)

    settings = resolve_tracing_settings(DEFAULT_SERVICE_NAME_FOR_TESTS)

    assert settings.service_name == DEFAULT_SERVICE_NAME_FOR_TESTS
    assert settings.exporter_endpoint == DEFAULT_EXPORTER_ENDPOINT
    assert settings.sampler_ratio == 1.0
    assert not settings.is_enabled


def test_environment_overrides_service_name_and_endpoint(monkeypatch):
    monkeypatch.setenv(ENVIRONMENT_VARIABLE_SERVICE_NAME, "read-service")
    monkeypatch.setenv(ENVIRONMENT_VARIABLE_EXPORTER_ENDPOINT, "http://jaeger:4317")

    settings = resolve_tracing_settings(DEFAULT_SERVICE_NAME_FOR_TESTS)

    assert settings.service_name == "read-service"
    assert settings.exporter_endpoint == "http://jaeger:4317"


def test_tracing_is_enabled_once_an_exporter_endpoint_is_configured(monkeypatch):
    monkeypatch.delenv(ENVIRONMENT_VARIABLE_SDK_DISABLED, raising=False)
    monkeypatch.setenv(ENVIRONMENT_VARIABLE_EXPORTER_ENDPOINT, "http://jaeger:4317")

    assert resolve_tracing_settings(DEFAULT_SERVICE_NAME_FOR_TESTS).is_enabled


def test_sdk_disabled_flag_wins_over_a_configured_endpoint(monkeypatch):
    monkeypatch.setenv(ENVIRONMENT_VARIABLE_EXPORTER_ENDPOINT, "http://jaeger:4317")
    monkeypatch.setenv(ENVIRONMENT_VARIABLE_SDK_DISABLED, "true")

    assert not resolve_tracing_settings(DEFAULT_SERVICE_NAME_FOR_TESTS).is_enabled


def test_unparsable_sampler_ratio_falls_back_to_full_sampling(monkeypatch):
    monkeypatch.setenv(ENVIRONMENT_VARIABLE_SAMPLER_RATIO, "not-a-number")

    assert resolve_tracing_settings(DEFAULT_SERVICE_NAME_FOR_TESTS).sampler_ratio == 1.0
