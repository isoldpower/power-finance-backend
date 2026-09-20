package sandbox

import (
	"context"
	"testing"

	"github.com/power-finance/kafka-client-go/headers"
	"go.opentelemetry.io/otel"
	otelpropagation "go.opentelemetry.io/otel/propagation"
)

func init() {
	otel.SetTextMapPropagator(otelpropagation.NewCompositeTextMapPropagator(
		otelpropagation.TraceContext{},
		otelpropagation.Baggage{},
	))
}

func TestScopeGroupIDLeavesBaselineUntouched(t *testing.T) {
	if scoped := ScopeGroupID("webhook-service", ""); scoped != "webhook-service" {
		t.Fatalf("expected baseline group id unchanged, got %q", scoped)
	}
}

func TestScopeGroupIDSuffixesSandbox(t *testing.T) {
	if scoped := ScopeGroupID("webhook-service", "nikita"); scoped != "webhook-service-sbx-nikita" {
		t.Fatalf("expected suffixed group id, got %q", scoped)
	}
}

func TestReadIDFromHeadersFindsSandboxEntry(t *testing.T) {
	kafkaHeaders := headers.KafkaHeaders{
		headers.String("traceparent", "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"),
		headers.String("baggage", "request-id=abc,sandbox-id=nikita"),
	}

	if sandboxID := ReadIDFromHeaders(kafkaHeaders); sandboxID != "nikita" {
		t.Fatalf("expected nikita, got %q", sandboxID)
	}
}

func TestReadIDFromHeadersIsEmptyForBaselineTraffic(t *testing.T) {
	kafkaHeaders := headers.KafkaHeaders{
		headers.String("baggage", "request-id=abc"),
	}

	if sandboxID := ReadIDFromHeaders(kafkaHeaders); sandboxID != "" {
		t.Fatalf("expected empty sandbox id, got %q", sandboxID)
	}
}

func TestReadIDFromHeadersIsEmptyWithoutBaggage(t *testing.T) {
	if sandboxID := ReadIDFromHeaders(headers.KafkaHeaders{}); sandboxID != "" {
		t.Fatalf("expected empty sandbox id, got %q", sandboxID)
	}
}

func TestReadIDFromHeadersIgnoresEntryProperties(t *testing.T) {
	kafkaHeaders := headers.KafkaHeaders{
		headers.String("baggage", "sandbox-id=nikita;meta=1"),
	}

	if sandboxID := ReadIDFromHeaders(kafkaHeaders); sandboxID != "nikita" {
		t.Fatalf("expected nikita, got %q", sandboxID)
	}
}

func TestAttachIDRoundTripsThroughContext(t *testing.T) {
	ctx := AttachID(context.Background(), "nikita")

	if sandboxID := CurrentID(ctx); sandboxID != "nikita" {
		t.Fatalf("expected nikita, got %q", sandboxID)
	}
}

func TestCurrentIDIsEmptyOnABareContext(t *testing.T) {
	if sandboxID := CurrentID(context.Background()); sandboxID != "" {
		t.Fatalf("expected empty sandbox id, got %q", sandboxID)
	}
}

func TestResolveOwnIDTrimsWhitespace(t *testing.T) {
	t.Setenv(EnvironmentVariableID, "   ")

	if ownID := ResolveOwnID(); ownID != "" {
		t.Fatalf("expected blank sandbox id to resolve empty, got %q", ownID)
	}
}
