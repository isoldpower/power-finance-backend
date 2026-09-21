package tracing

import (
	"context"

	"go.opentelemetry.io/otel/trace"
)

// CurrentTraceIDHex returns the active trace id, empty when nothing is sampled.
func CurrentTraceIDHex(ctx context.Context) string {
	spanContext := trace.SpanContextFromContext(ctx)
	if !spanContext.HasTraceID() {
		return ""
	}

	return spanContext.TraceID().String()
}

// CurrentSpanIDHex returns the active span id, empty when nothing is sampled.
func CurrentSpanIDHex(ctx context.Context) string {
	spanContext := trace.SpanContextFromContext(ctx)
	if !spanContext.HasSpanID() {
		return ""
	}

	return spanContext.SpanID().String()
}
