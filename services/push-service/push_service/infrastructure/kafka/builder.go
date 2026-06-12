package kafka

import (
	"context"
	"fmt"
	"strings"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/consumer"
	"github.com/power-finance/kafka-client-go/envelope"
	"github.com/power-finance/kafka-client-go/headers"
	"github.com/power-finance/kafka-client-go/publisher"
	"github.com/twmb/franz-go/pkg/kgo"

	"services/push-service/push_service/services"
)

func BuildNotificationsConsumerLoop(
	ctx context.Context,
	config ConsumerConfig,
	eventsSink chan<- services.OutboxEvent,
) (*ConsumerLoop, error) {
	failurePublisher, publisherErr := buildFailurePublisher(ctx, config)
	if publisherErr != nil {
		return nil, fmt.Errorf("kafka: failure publisher: %w", publisherErr)
	}

	messageHandler := consumer.NewMessageHandler(
		newEventsSinkHandler(eventsSink),
		consumer.MessageHandlerConfig{
			Policy:         consumer.DefaultRetryPolicy(),
			RetryPublisher: publisher.NewRetryPublisher(failurePublisher, config.RetryTopic),
			DLQPublisher:   publisher.NewDLQPublisher(failurePublisher, config.DLQTopic),
			EventID:        extractEnvelopeEventID,
		},
	)

	groupClient, clientErr := kgo.NewClient(
		kgo.SeedBrokers(strings.Split(config.BootstrapServers, ",")...),
		kgo.ClientID(clientID),
		kgo.ConsumerGroup(config.GroupID),
		kgo.ConsumeTopics(config.Topics...),
		kgo.DisableAutoCommit(),
		kgo.FetchIsolationLevel(kgo.ReadCommitted()),
		kgo.ConsumeResetOffset(kgo.NewOffset().AtEnd()),
	)
	if clientErr != nil {
		failurePublisher.Stop()
		return nil, fmt.Errorf("kafka: consumer group client: %w", clientErr)
	}

	return NewConsumerLoop(groupClient, messageHandler), nil
}

func buildFailurePublisher(
	ctx context.Context,
	config ConsumerConfig,
) (*publisher.KafkaPublisher, error) {
	producerConfig := publisher.DefaultProducerConfig(config.BootstrapServers)
	producerConfig.ClientID = clientID

	failurePublisher := publisher.NewKafkaPublisher(producerConfig)
	if startErr := failurePublisher.Start(ctx); startErr != nil {
		return nil, startErr
	}

	return failurePublisher, nil
}

func newEventsSinkHandler(eventsSink chan<- services.OutboxEvent) consumer.UserHandler {
	return func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		select {
		case eventsSink <- outboxEventFromMessage(message):
			return nil
		case <-ctx.Done():
			return ctx.Err()
		}
	}
}

func outboxEventFromMessage(message kafkaclient.ConsumedMessage) services.OutboxEvent {
	eventID, _ := headers.Get(message.Headers, envelope.EventID)
	eventType, _ := headers.Get(message.Headers, envelope.EventType)
	aggregateType, _ := headers.Get(message.Headers, envelope.AggregateType)

	return services.OutboxEvent{
		EventID:       eventID,
		EventType:     eventType,
		AggregateType: aggregateType,
		UserID:        string(message.Key),
		Payload:       message.Value,
	}
}

func extractEnvelopeEventID(message kafkaclient.ConsumedMessage) (string, bool) {
	return headers.Get(message.Headers, envelope.EventID)
}
