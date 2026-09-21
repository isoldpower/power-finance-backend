# correlation-py

Request-scoped correlation and sandbox binding for the Django services. It is a
thin layer over the OpenTelemetry context that `observability-py` owns.

## What changed when tracing arrived

`get_correlation_id()` used to return a per-request UUID held in a `ContextVar`.
It now returns **the active trace id**, falling back to the `ContextVar` when no
span is active. Call sites did not change: the `request_id` field in both
services' HTTP envelopes is now a real trace id, so a value a client sees in a
response can be pasted into Jaeger.

`get_bound_correlation_id()` returns the raw `ContextVar` value when you
specifically need what the middleware bound rather than the trace id.

## Layout

| Module | Holds |
|---|---|
| `middleware.py` | `CorrelationIDMiddleware`, which picks the sync or async propagator |
| `context_propagator/` | the propagators; they bracket the request and stamp the response |
| `request_scope/` | `CorrelationBinder`, `SandboxBinder` and the `RequestScopeBinder` that composes them |
| `utilities/` | header-name settings and the correlation `ContextVar` |
| `logging.py` | `CorrelationIDFilter`, plus a re-export of `observability.TraceContextFilter` |

The propagators hold no binding logic of their own — sync and async differ only in
the `await`.

## Request scope

Per request, `RequestScopeBinder` binds two things:

- **correlation id** — from the `X-Correlation-ID` header, else the active trace
  id, else a fresh UUID. Echoed back on the response and attached to the request
  as `request.correlation_id`.
- **sandbox id** — from the `X-Sandbox` header into OpenTelemetry baggage, and
  attached as `request.sandbox_id`. Nothing is re-attached when the sandbox id
  already arrived in the `baggage` header (the gateway's `sandbox-router` plugin
  puts it there), so context is bound once per request.

## Settings

| Django setting | Default |
|---|---|
| `CORRELATION_ID_HEADER` | `X-Correlation-ID` |
| `SANDBOX_ID_HEADER` | `X-Sandbox` |

## Logging

Register both filters to get correlation and trace fields on every record:

```python
"filters": {
    "correlation_id": {"()": "correlation.CorrelationIDFilter"},
    "trace_context": {"()": "observability.TraceContextFilter"},
},
```

`CorrelationIDFilter` sets `correlation_id`; `TraceContextFilter` sets `trace_id`,
`span_id` and `sandbox_id`. Missing values render as `-`.

## Tests

```bash
uv run pytest libraries/correlation-py -q
```
