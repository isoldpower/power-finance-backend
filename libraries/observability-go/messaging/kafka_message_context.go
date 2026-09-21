package messaging

import (
	"context"

	"github.com/power-finance/kafka-client-go/headers"
	"github.com/power-finance/observability-go/propagation"
	"github.com/power-finance/observability-go/sandbox"
)

// MessageContextBinder re-attaches a produced context to the consuming side.
type MessageContextBinder struct{}

func NewMessageContextBinder() MessageContextBinder {
	return MessageContextBinder{}
}

// Bind returns the context a message should be handled under.
func (MessageContextBinder) Bind(
	ctx context.Context,
	kafkaHeaders headers.KafkaHeaders,
) context.Context {
	return propagation.ExtractFromKafkaHeaders(ctx, kafkaHeaders)
}

// ReadSandboxID reports which sandbox a message belongs to, empty for baseline.
func (MessageContextBinder) ReadSandboxID(kafkaHeaders headers.KafkaHeaders) string {
	return sandbox.ReadIDFromHeaders(kafkaHeaders)
}

// KafkaMessageContextComponents is what a consumer needs to honour both the
// trace context on a message and the sandbox that owns it.
type KafkaMessageContextComponents struct {
	ContextBinder MessageContextBinder
	TrafficPolicy sandbox.TrafficMatcher
}

func BuildKafkaMessageContextComponents() KafkaMessageContextComponents {
	return KafkaMessageContextComponents{
		ContextBinder: NewMessageContextBinder(),
		TrafficPolicy: sandbox.NewTrafficMatcherFromEnvironment(),
	}
}
