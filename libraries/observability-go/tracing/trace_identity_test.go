package tracing

import (
	"context"
	"testing"

	"go.opentelemetry.io/otel"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// The default provider is a noop and mints no ids; a service gets a real one
// from Configure, so the tests install the same kind.
func init() {
	otel.SetTracerProvider(sdktrace.NewTracerProvider(
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
	))
}

func TestTraceIdentityIsEmptyOnABareContext(t *testing.T) {
	if traceID := CurrentTraceIDHex(context.Background()); traceID != "" {
		t.Fatalf("expected an empty trace id, got %q", traceID)
	}
	if spanID := CurrentSpanIDHex(context.Background()); spanID != "" {
		t.Fatalf("expected an empty span id, got %q", spanID)
	}
}

func TestTraceIdentityReadsARecordingSpan(t *testing.T) {
	ctx, endSpan := StartConsumerSpan(context.Background(), "test consume", "events.async")
	defer endSpan()

	if traceID := CurrentTraceIDHex(ctx); len(traceID) != 32 {
		t.Fatalf("expected a 32-character trace id, got %q", traceID)
	}
	if spanID := CurrentSpanIDHex(ctx); len(spanID) != 16 {
		t.Fatalf("expected a 16-character span id, got %q", spanID)
	}
}
