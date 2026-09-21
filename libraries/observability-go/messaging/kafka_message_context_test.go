package messaging

import (
	"context"
	"testing"

	"github.com/power-finance/kafka-client-go/headers"
	"github.com/power-finance/observability-go/propagation"
	"github.com/power-finance/observability-go/sandbox"
	"go.opentelemetry.io/otel"
	otelpropagation "go.opentelemetry.io/otel/propagation"
)

func init() {
	otel.SetTextMapPropagator(otelpropagation.NewCompositeTextMapPropagator(
		otelpropagation.TraceContext{},
		otelpropagation.Baggage{},
	))
}

func TestBindReattachesTheProducedBaggage(t *testing.T) {
	produced := sandbox.AttachID(context.Background(), "nikita")
	kafkaHeaders := propagation.InjectIntoKafkaHeaders(produced)

	bound := NewMessageContextBinder().Bind(context.Background(), kafkaHeaders)

	if sandboxID := sandbox.CurrentID(bound); sandboxID != "nikita" {
		t.Fatalf("expected the baggage to survive the hop, got %q", sandboxID)
	}
}

func TestBindOnAMessageWithoutContextLeavesTheContextBare(t *testing.T) {
	bound := NewMessageContextBinder().Bind(context.Background(), headers.KafkaHeaders{})

	if sandboxID := sandbox.CurrentID(bound); sandboxID != "" {
		t.Fatalf("expected an empty sandbox id, got %q", sandboxID)
	}
}

func TestReadSandboxIDMatchesWhatWasProduced(t *testing.T) {
	kafkaHeaders := propagation.InjectIntoKafkaHeaders(
		sandbox.AttachID(context.Background(), "anna"),
	)

	if sandboxID := NewMessageContextBinder().ReadSandboxID(kafkaHeaders); sandboxID != "anna" {
		t.Fatalf("expected anna, got %q", sandboxID)
	}
}

func TestReadSandboxIDIsEmptyForBaselineTraffic(t *testing.T) {
	if sandboxID := NewMessageContextBinder().ReadSandboxID(headers.KafkaHeaders{}); sandboxID != "" {
		t.Fatalf("expected empty sandbox id, got %q", sandboxID)
	}
}

func TestComponentsTakeTheTrafficPolicyFromTheEnvironment(t *testing.T) {
	t.Setenv(sandbox.EnvironmentVariableID, "nikita")

	components := BuildKafkaMessageContextComponents()

	if components.TrafficPolicy.OwnSandboxID() != "nikita" {
		t.Fatalf("unexpected own sandbox id %q", components.TrafficPolicy.OwnSandboxID())
	}
	if components.TrafficPolicy.IsBaseline() {
		t.Fatal("expected a sandbox policy, not a baseline one")
	}
}

func TestComponentsRouteAMessageToItsOwner(t *testing.T) {
	t.Setenv(sandbox.EnvironmentVariableID, "nikita")
	components := BuildKafkaMessageContextComponents()

	own := propagation.InjectIntoKafkaHeaders(sandbox.AttachID(context.Background(), "nikita"))
	foreign := propagation.InjectIntoKafkaHeaders(sandbox.AttachID(context.Background(), "anna"))

	if !components.TrafficPolicy.IsOwnedTraffic(components.ContextBinder.ReadSandboxID(own)) {
		t.Fatal("expected the sandbox to own its own message")
	}
	if components.TrafficPolicy.IsOwnedTraffic(components.ContextBinder.ReadSandboxID(foreign)) {
		t.Fatal("expected another sandbox's message to be skipped")
	}
	if components.TrafficPolicy.IsOwnedTraffic(components.ContextBinder.ReadSandboxID(headers.KafkaHeaders{})) {
		t.Fatal("expected baseline traffic to be skipped by a sandbox")
	}
}
