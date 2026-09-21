import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider


@pytest.fixture(scope="session", autouse=True)
def installed_tracer_provider() -> TracerProvider:
    tracer_provider = TracerProvider()
    trace.set_tracer_provider(tracer_provider)

    return tracer_provider


@pytest.fixture
def tracer() -> trace.Tracer:
    return trace.get_tracer("observability-tests")
