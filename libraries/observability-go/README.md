# observability-go

The Go counterpart to `observability-py`: OpenTelemetry tracing bootstrap and W3C
context propagation for `push-service` and `webhook-service`. It owns every
OpenTelemetry import on the Go side, so the services and `kafka-client-go` stay
free of the SDK.

## Packages

| Package | Holds |
| --- | --- |
| `tracing` | `Configure` (provider + exporter + propagators), `WrapHTTPHandler`, `StartConsumerSpan`, settings resolved from `OTEL_*` |
| `propagation` | `ExtractFromKafkaHeaders` and the `KafkaHeaderCarrier` it reads through |

## Wiring a service

```go
_, shutdownTracing, tracingErr := tracing.Configure(ctx, "webhook-service")
if tracingErr != nil {
    return tracingErr
}
defer func() {
    shutdownContext, cancel := context.WithTimeout(context.Background(), tracing.ShutdownTimeout())
    defer cancel()
    _ = shutdownTracing(shutdownContext)
}()
```

HTTP servers wrap their handler; consumers extract the producer's context and open
a span of their own:

```go
Handler: tracing.WrapHTTPHandler(router, "webhook-service"),

ctx = propagation.ExtractFromKafkaHeaders(ctx, message.Headers)
ctx, endSpan := tracing.StartConsumerSpan(ctx, "webhook deliveries consume", message.Topic)
defer endSpan()
```

**Configuring the SDK is not enough to appear in Jaeger.** A service that only
installs a provider and propagates context emits no spans of its own and never
shows up — the HTTP wrapper and the consumer span are what make it visible, and
the consumer span is what attaches this service to the producer's trace.

## Environment

Same contract as `observability-py`, so one set of variables configures both:

| Variable | Default | Meaning |
| --- | --- | --- |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | unset | OTLP/gRPC collector. **Unset means tracing is off.** |
| `OTEL_SERVICE_NAME` | the `Configure` argument | service name on every span |
| `OTEL_SDK_DISABLED` | `false` | hard off switch |
| `OTEL_TRACES_SAMPLER_ARG` | `1.0` | parent-based sampler ratio |
| `OTEL_DEPLOYMENT_ENVIRONMENT` | `development` | resource attribute |

The endpoint may carry an `http://` scheme; it is stripped, because the gRPC
exporter wants host:port.

## Sandbox isolation lives elsewhere

Deciding which process owns a message is `kafka-client-go/sandbox` — deliberately
standard-library only, so the isolation path carries no OpenTelemetry dependency.
This module only makes the trace continuous.

## Module layout

A separate Go module, wired through `go.work` for local development and through
`replace` directives for the Docker builds, which have no workspace. **Both
service images must copy `libraries/observability-go` and their `go.mod`/`go.sum`
must be tidied**, or the image build fails with *"updates to go.mod needed"*.
