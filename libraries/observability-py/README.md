# observability-py

OpenTelemetry tracing bootstrap, W3C context propagation, and sandbox baggage for
the Python services. It owns every OpenTelemetry import in the workspace — other
libraries depend on structural ports instead, so nothing else has to know the SDK
exists.

## Why this library carries sandbox routing

The shared dev environment runs **one** baseline stack and gives each developer a
sandbox holding only the service they changed. Isolation is decided per request,
so the sandbox id has to travel with the request — across HTTP, through the
outbox table, and out over Kafka.

Rather than threading a dev-only `sandbox_id` field through every producer and
consumer, this library propagates the **standard** W3C pair, `traceparent` and
`baggage`, and treats `sandbox-id` as one baggage entry. The same work makes
distributed tracing possible, and future propagated values cost one baggage key
instead of another migration.

**Baggage, never the trace id.** Baggage propagates regardless of the sampling
decision, and a trace id is unique per request — there is nothing stable to match
a route against. Routing reads baggage; correlation reads the trace id.

## Layout

| Package | Holds |
|---|---|
| `configuration/` | `TracingSettings`, resolved from `OTEL_*` environment variables |
| `tracing/` | tracer-provider factory, the instrumentation registry and its activators, and `configure_tracing` |
| `context/` | carrier getters, inject/extract, baggage entry access, current trace/span ids |
| `sandbox/` | the `sandbox-id` baggage key, `X-Sandbox` header name, and `SandboxTrafficMatcher` |
| `messaging/` | `OutboxTraceContext` (what an outbox row stores) and `KafkaMessageContextBinder` |
| `logging/` | `TraceContextFilter`, which stamps `trace_id`, `span_id` and `sandbox_id` onto log records |

## Configuring a service

```python
from observability import (
    DjangoInstrumentationActivator,
    PsycopgInstrumentationActivator,
    configure_tracing,
)

configure_tracing(
    default_service_name="write-service",
    instrumentation_activators=(
        DjangoInstrumentationActivator(),
        PsycopgInstrumentationActivator(),
    ),
)
```

### Django must be wrapped, not just instrumented

`DjangoInstrumentationActivator` alone is **not enough for a Django service served
over ASGI**. The OpenTelemetry Django middleware attaches its span inside a
`sync_to_async` worker call, and asgiref discards context changes when that call
returns — so the span never becomes current in view code, `get_correlation_id()`
sees no trace, and `capture_outbox_trace_context()` returns empty. The symptom is
`trace=-` in the logs and NULL propagation columns while the exporter is otherwise
healthy.

Wrap the application itself, which creates the server span in the event loop where
everything downstream inherits it:

```python
application = wrap_asgi_application(get_asgi_application())   # ASGI
application = wrap_wsgi_application(get_wsgi_application())   # WSGI
```

Keep the Django activator as well — its span becomes a child and adds view detail.
FastAPI needs no wrapper; `FastapiInstrumentationActivator` is native ASGI.

`configure_tracing` is idempotent — calling it from both an ASGI gateway and a
Django `AppConfig.ready()` installs one provider. Activators import their
instrumentation package lazily, so a missing optional extra is logged and skipped
rather than crashing the service.

**Tracing stays off until `OTEL_EXPORTER_OTLP_ENDPOINT` is set.** A developer
running a service on their laptop produces no spans and no exporter errors; the
baseline and sandbox compose profiles set the endpoint and turn it on.

### Environment

| Variable | Default | Meaning |
|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | unset | OTLP/gRPC collector. **Unset means tracing is disabled.** |
| `OTEL_SERVICE_NAME` | the `default_service_name` argument | Service name on every span |
| `OTEL_SDK_DISABLED` | `false` | Hard off switch; wins over a configured endpoint |
| `OTEL_TRACES_SAMPLER_ARG` | `1.0` | Ratio for the parent-based sampler; `>= 1.0` means always on |
| `OTEL_DEPLOYMENT_ENVIRONMENT` | `development` | `deployment.environment` resource attribute |
| `SANDBOX_ID` | empty | This process's sandbox. Empty means baseline. |

## The outbox hop

Debezium publishes outbox rows, so in-process context does not reach the
consumer — the context has to be **stored in the row**:

1. `capture_outbox_trace_context()` runs inside the producing request's span and
   returns `traceparent` / `tracestate` / `baggage`.
2. The service writes those three into its outbox table.
3. The Debezium connector's `transforms.outbox.table.fields.additional.placement`
   copies them onto the Kafka record as headers of the same names.
4. `KafkaMessageContextBinder.bind(record.headers)` re-attaches the context in the
   consumer, so its spans join the producer's trace and its logs carry the ids.

The producer's span has already ended by the time Debezium ships the row, so the
consumer span is a **child of a finished span** rather than nested inside it. That
is what OpenTelemetry's messaging convention models; it is not a bug.

## Baselines and sandboxes

`SandboxTrafficMatcher` decides who owns a message:

| Process | `SANDBOX_ID` | Owns |
|---|---|---|
| baseline | empty | messages with no `sandbox-id` |
| sandbox | `nikita` | messages whose `sandbox-id` is `nikita` |

Exactly one consumer owns any given message, which is what keeps a sandbox from
eating baseline traffic. A sandbox must also run under its own Kafka consumer
group — see `kafka-consumer-py`'s `resolve_sandbox_scoped_group_id`.

**Never put PII in baggage.** It propagates to every downstream service and is
written into Kafka record headers. `sandbox-id` only.

## Tests

```bash
uv run pytest libraries/observability-py -q
```
