package propagation

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

func TestBaggageEntryRoundTrips(t *testing.T) {
	ctx := WriteBaggageEntry(context.Background(), "sandbox-id", "nikita")

	if value := ReadBaggageEntry(ctx, "sandbox-id"); value != "nikita" {
		t.Fatalf("expected nikita, got %q", value)
	}
}

func TestReadBaggageEntryIsEmptyWhenAbsent(t *testing.T) {
	if value := ReadBaggageEntry(context.Background(), "sandbox-id"); value != "" {
		t.Fatalf("expected empty value, got %q", value)
	}
}

func TestWriteBaggageEntryKeepsExistingEntries(t *testing.T) {
	ctx := WriteBaggageEntry(context.Background(), "request-id", "abc")
	ctx = WriteBaggageEntry(ctx, "sandbox-id", "nikita")

	if value := ReadBaggageEntry(ctx, "request-id"); value != "abc" {
		t.Fatalf("expected the first entry to survive, got %q", value)
	}
	if value := ReadBaggageEntry(ctx, "sandbox-id"); value != "nikita" {
		t.Fatalf("expected nikita, got %q", value)
	}
}

func TestWriteBaggageEntryRejectsAnUnrepresentableValueWithoutFailing(t *testing.T) {
	ctx := WriteBaggageEntry(context.Background(), "", "nikita")

	if value := ReadBaggageEntry(ctx, ""); value != "" {
		t.Fatalf("expected the entry to be dropped, got %q", value)
	}
}

func TestInjectedContextIsExtractable(t *testing.T) {
	ctx := WriteBaggageEntry(context.Background(), "sandbox-id", "nikita")

	extracted := ExtractFromKafkaHeaders(context.Background(), InjectIntoKafkaHeaders(ctx))

	if value := ReadBaggageEntry(extracted, "sandbox-id"); value != "nikita" {
		t.Fatalf("expected the baggage to survive a round trip, got %q", value)
	}
}

func TestKafkaHeaderCarrierReadsAndListsHeaders(t *testing.T) {
	carrier := NewKafkaHeaderCarrier(headers.KafkaHeaders{
		headers.String("baggage", "sandbox-id=nikita"),
	})

	if value := carrier.Get("baggage"); value != "sandbox-id=nikita" {
		t.Fatalf("unexpected carrier value %q", value)
	}
	if value := carrier.Get("absent"); value != "" {
		t.Fatalf("expected empty value for a missing key, got %q", value)
	}
	if keys := carrier.Keys(); len(keys) != 1 || keys[0] != "baggage" {
		t.Fatalf("unexpected carrier keys %v", keys)
	}
}
