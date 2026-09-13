package sandbox

import (
	"testing"

	"github.com/power-finance/kafka-client-go/headers"
)

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

func TestReadBaggageEntryIgnoresEntryProperties(t *testing.T) {
	if value := ReadBaggageEntry("sandbox-id=nikita;meta=1", "sandbox-id"); value != "nikita" {
		t.Fatalf("expected nikita, got %q", value)
	}
}

func TestBaselineMatcherOwnsUntaggedTrafficOnly(t *testing.T) {
	matcher := NewTrafficMatcher("")

	if !matcher.IsBaseline() {
		t.Fatal("expected baseline matcher")
	}
	if !matcher.IsOwnedTraffic("") {
		t.Fatal("baseline should own untagged traffic")
	}
	if matcher.IsOwnedTraffic("nikita") {
		t.Fatal("baseline should not own sandbox traffic")
	}
}

func TestSandboxMatcherOwnsItsOwnTrafficOnly(t *testing.T) {
	matcher := NewTrafficMatcher("nikita")

	if matcher.IsBaseline() {
		t.Fatal("expected sandbox matcher")
	}
	if !matcher.IsOwnedTraffic("nikita") {
		t.Fatal("sandbox should own its own traffic")
	}
	if matcher.IsOwnedTraffic("") {
		t.Fatal("sandbox should not own baseline traffic")
	}
	if matcher.IsOwnedTraffic("someone-else") {
		t.Fatal("sandbox should not own another sandbox's traffic")
	}
}

func TestMatcherFromEnvironmentTrimsBlankValue(t *testing.T) {
	t.Setenv(EnvironmentVariableID, "   ")

	if !NewTrafficMatcherFromEnvironment().IsBaseline() {
		t.Fatal("blank SANDBOX_ID should mean baseline")
	}
}
