package tracing

import (
	"context"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
)

const tracerName = "github.com/power-finance/observability-go"

type SpanEndFunc func()

func StartConsumerSpan(
	ctx context.Context,
	operationName string,
	topic string,
) (context.Context, SpanEndFunc) {
	spanContext, span := otel.Tracer(tracerName).Start(
		ctx,
		operationName,
		trace.WithSpanKind(trace.SpanKindConsumer),
		trace.WithAttributes(attribute.String("messaging.destination.name", topic)),
	)

	return spanContext, func() { span.End() }
}
