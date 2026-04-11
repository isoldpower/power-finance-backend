# Distributed Tracing with OpenTelemetry

## Why

When a request enters Django, triggers a Celery task, which writes to PostgreSQL and publishes to RabbitMQ — you have a distributed system. When something is slow or broken, you need to see the full picture across all components in one trace. Without this, k8s debugging is guesswork.

## Production Concepts Taught

- Distributed tracing concepts: spans, traces, context propagation
- OpenTelemetry SDK instrumentation (Django, Celery, SQLAlchemy, Redis)
- Trace context propagation across service boundaries (HTTP headers, message queues)
- Exporting to observability backends (Jaeger, Tempo, Honeycomb)
- Structured logging correlation (trace_id in log lines)
- Performance profiling via span duration analysis
- Sampling strategies (always-on vs. probabilistic vs. tail-based)

## Core Concepts

```
Trace: one complete request journey (e.g., POST /transactions → DB → Celery → webhook)
Span:  one unit of work within a trace (e.g., "postgres query", "celery task")
Context propagation: passing trace_id across process boundaries

HTTP:          traceparent header (W3C Trace Context standard)
Celery tasks:  inject context into task headers, extract on worker side
```

## Instrumentation Targets

| Component | Library | What Gets Traced |
|---|---|---|
| Django HTTP | `opentelemetry-instrumentation-django` | All HTTP requests, status codes, route |
| PostgreSQL | `opentelemetry-instrumentation-psycopg2` | Every SQL query with duration |
| Redis | `opentelemetry-instrumentation-redis` | Every Redis command |
| Celery | `opentelemetry-instrumentation-celery` | Task enqueue, execute, result |
| Requests (outbound webhooks) | `opentelemetry-instrumentation-requests` | HTTP calls to webhook endpoints |

## Setup

```python
# telemetry.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor

def setup_telemetry():
    provider = TracerProvider(
        resource=Resource.create({
            SERVICE_NAME: "power-finance-api",
            SERVICE_VERSION: settings.APP_VERSION,
            DEPLOYMENT_ENVIRONMENT: settings.ENVIRONMENT,
        })
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint="http://jaeger:4317"))
    )
    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    RedisInstrumentor().instrument()
    CeleryInstrumentor().instrument()
```

## Custom Spans for Business Logic

Auto-instrumentation covers infrastructure. Add custom spans for domain logic:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class CreateTransactionUseCase:
    def execute(self, command):
        with tracer.start_as_current_span("create_transaction") as span:
            span.set_attribute("transaction.type", command.type.value)
            span.set_attribute("transaction.amount", str(command.amount.value))
            span.set_attribute("wallet.id", str(command.wallet_id))
            # ... use case logic
```

## Trace Context in Logs

Correlate log lines to traces by injecting trace_id:

```python
import logging
from opentelemetry import trace

class TraceIdFilter(logging.Filter):
    def filter(self, record):
        span = trace.get_current_span()
        ctx = span.get_span_context()
        record.trace_id = format(ctx.trace_id, '032x') if ctx.is_valid else 'no-trace'
        record.span_id = format(ctx.span_id, '016x') if ctx.is_valid else 'no-span'
        return True
```

Log format: `[trace_id=abc123 span_id=def456] POST /transactions 201 45ms`

## Celery Context Propagation

Celery crosses process boundaries — trace context must travel with the task:

```python
# Auto-handled by opentelemetry-instrumentation-celery
# It injects W3C traceparent into task headers on enqueue
# and extracts + resumes the trace on the worker side

# Result: webhook delivery task appears as child span of the
# original HTTP request that triggered the domain event
```

## k8s / Docker Compose Setup

Add Jaeger to `compose.yaml`:

```yaml
jaeger:
  image: jaegertracing/all-in-one:latest
  ports:
    - "16686:16686"   # UI
    - "4317:4317"     # OTLP gRPC
  environment:
    COLLECTOR_OTLP_ENABLED: "true"
```

Access traces at `http://localhost:16686`.

## Sampling Strategy

| Environment | Strategy | Why |
|---|---|---|
| Development | Always sample (1.0) | See everything |
| Production | 10% probabilistic or tail-based | Control volume/cost |

Tail-based sampling (sample 100% of errors, 10% of success) requires a collector like OpenTelemetry Collector.

## Key Blockwalls

- Context propagation across Celery — must use instrumentation library, not manual; task serialization drops context if not handled
- Async Django (ASGI) — context propagation differs from sync; `contextvars` required
- Span cardinality explosion — don't use user_id as span attribute if you have millions of users; use it as trace attribute instead
- Sampling before vs. after — head sampling (decide at request start) vs. tail sampling (decide after seeing full trace)
