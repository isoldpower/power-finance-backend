package kafka

import (
	"context"
	"fmt"
	"log/slog"
	"strings"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/envelope"
	"github.com/power-finance/kafka-client-go/headers"
	"github.com/power-finance/observability-go/messaging"
	"github.com/power-finance/observability-go/tracing"
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
	broadcastClient, clientErr := buildBroadcastClient(
		ctx,
		kafkaConfig.BootstrapServers,
		kgo.ConsumeTopics(kafkaConfig.OutboxTopics...),
		kgo.FetchIsolationLevel(kgo.ReadCommitted()),
	)
	if clientErr != nil {
		return nil, clientErr
	}

	return NewConsumerLoop(broadcastClient, newEventsSinkHandler(eventsSink), readinessProbe), nil
}

func BuildDemoSpansConsumerLoop(
	ctx context.Context,
	kafkaConfig types.KafkaConfig,
	spansSink chan<- types.OutboxEvent,
	readinessProbe *health.Probe,
) (*ConsumerLoop, error) {
	broadcastClient, clientErr := buildBroadcastClient(
		ctx,
		kafkaConfig.BootstrapServers,
		kgo.ConsumeTopics(kafkaConfig.DemoSpansTopic),
		kgo.AllowAutoTopicCreation(),
	)
	if clientErr != nil {
		return nil, clientErr
	}

	return NewConsumerLoop(broadcastClient, newDemoSpansSinkHandler(spansSink), readinessProbe), nil
}

func buildBroadcastClient(
	ctx context.Context,
	bootstrapServers string,
	consumptionOptions ...kgo.Opt,
) (*kgo.Client, error) {
	clientOptions := append(
		[]kgo.Opt{
			kgo.SeedBrokers(strings.Split(bootstrapServers, ",")...),
			kgo.ClientID(clientID),
			kgo.ConsumeResetOffset(kgo.NewOffset().AtEnd()),
		},
		consumptionOptions...,
	)
	broadcastClient, clientErr := kgo.NewClient(clientOptions...)
	if clientErr != nil {
		return nil, fmt.Errorf("kafka: broadcast consumer client: %w", clientErr)
	}

	if pingErr := broadcastClient.Ping(ctx); pingErr != nil {
		broadcastClient.Close()
		return nil, fmt.Errorf("kafka: broker unreachable: %w", pingErr)
	}

	return broadcastClient, nil
}

func newEventsSinkHandler(eventsSink chan<- types.OutboxEvent) MessageHandlerFunc {
	messageContext := messaging.BuildKafkaMessageContextComponents()

	return func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		ctx = messageContext.ContextBinder.Bind(ctx, message.Headers)
		messageSandboxID := messageContext.ContextBinder.ReadSandboxID(message.Headers)
		if !messageContext.TrafficPolicy.IsOwnedTraffic(messageSandboxID) {
			logForeignSandboxMessageSkipped(
				messageSandboxID,
				messageContext.TrafficPolicy.OwnSandboxID(),
			)
			return nil
		}

		ctx, endSpan := tracing.StartConsumerSpan(ctx, "notifications fanout consume", message.Topic)
		defer endSpan()

		select {
		case eventsSink <- outboxEventFromMessage(message):
			return nil
		case <-ctx.Done():
			return ctx.Err()
		}
	}
}

func newDemoSpansSinkHandler(spansSink chan<- types.OutboxEvent) MessageHandlerFunc {
	return func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		select {
		case spansSink <- types.OutboxEvent{Payload: message.Value}:
			return nil
		case <-ctx.Done():
			return ctx.Err()
		}
	}
}

func logForeignSandboxMessageSkipped(messageSandboxID string, ownSandboxID string) {
	slog.Debug(
		"kafka message belongs to another sandbox, skipping",
		"messageSandbox", messageSandboxID,
		"ownSandbox", ownSandboxID,
	)
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
