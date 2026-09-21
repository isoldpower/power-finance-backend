package sandbox

import (
	"context"
	"os"
	"strings"

	"github.com/power-finance/kafka-client-go/headers"
	"github.com/power-finance/observability-go/propagation"
)

// ResolveOwnID reports the sandbox this process belongs to, empty for the baseline.
func ResolveOwnID() string {
	return strings.TrimSpace(os.Getenv(EnvironmentVariableID))
}

// ScopeGroupID derives a sandbox's Kafka consumer group from the baseline's.
func ScopeGroupID(groupID string, sandboxID string) string {
	if sandboxID == "" {
		return groupID
	}

	return groupID + GroupIDSeparator + sandboxID
}

// CurrentID reads the sandbox id from the baggage already on the context.
func CurrentID(ctx context.Context) string {
	return propagation.ReadBaggageEntry(ctx, BaggageEntryName)
}

// AttachID returns a context carrying the sandbox id in W3C baggage.
func AttachID(ctx context.Context, sandboxID string) context.Context {
	return propagation.WriteBaggageEntry(ctx, BaggageEntryName, sandboxID)
}

// ReadIDFromHeaders extracts the propagated context from a Kafka message and
// reads the sandbox id out of its baggage.
func ReadIDFromHeaders(kafkaHeaders headers.KafkaHeaders) string {
	return CurrentID(propagation.ExtractFromKafkaHeaders(context.Background(), kafkaHeaders))
}
