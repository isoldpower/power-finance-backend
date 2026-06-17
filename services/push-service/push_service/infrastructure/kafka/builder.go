package kafka

import (
	"context"
	"fmt"
	"strings"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/envelope"
	"github.com/power-finance/kafka-client-go/headers"
	"github.com/twmb/franz-go/pkg/kgo"

	"services/push-service/internal/health"
	"services/push-service/push_service/types"
)

const clientID = "push-service"

// BuildNotificationsConsumerLoop builds a groupless broadcast consumer.
// Serves as a way to prevent racing for events between replicas.
func BuildNotificationsConsumerLoop(
	ctx context.Context,
	kafkaConfig types.KafkaConfig,
	eventsSink chan<- types.OutboxEvent,
	readinessProbe *health.Probe,
) (*ConsumerLoop, error) {
	broadcastClient, clientErr := kgo.NewClient(
		kgo.SeedBrokers(strings.Split(kafkaConfig.BootstrapServers, ",")...),
		kgo.ClientID(clientID),
		kgo.ConsumeTopics(kafkaConfig.OutboxTopics...),
		kgo.FetchIsolationLevel(kgo.ReadCommitted()),
		kgo.ConsumeResetOffset(kgo.NewOffset().AtEnd()),
	)
	if clientErr != nil {
		return nil, fmt.Errorf("kafka: broadcast consumer client: %w", clientErr)
	}

	if pingErr := broadcastClient.Ping(ctx); pingErr != nil {
		broadcastClient.Close()
		return nil, fmt.Errorf("kafka: broker unreachable: %w", pingErr)
	}

	return NewConsumerLoop(broadcastClient, newEventsSinkHandler(eventsSink), readinessProbe), nil
}

func newEventsSinkHandler(eventsSink chan<- types.OutboxEvent) MessageHandlerFunc {
	return func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		select {
		case eventsSink <- outboxEventFromMessage(message):
			return nil
		case <-ctx.Done():
			return ctx.Err()
		}
	}
}

func outboxEventFromMessage(message kafkaclient.ConsumedMessage) types.OutboxEvent {
	eventID, _ := headers.Get(message.Headers, envelope.EventID)
	eventType, _ := headers.Get(message.Headers, envelope.EventType)
	aggregateType, _ := headers.Get(message.Headers, envelope.AggregateType)

	return types.OutboxEvent{
		EventID:       eventID,
		EventType:     eventType,
		AggregateType: aggregateType,
		UserID:        string(message.Key),
		Payload:       message.Value,
	}
}
