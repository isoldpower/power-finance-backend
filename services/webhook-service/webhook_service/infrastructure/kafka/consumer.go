package kafka

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"strings"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/consumer"
	"github.com/power-finance/kafka-client-go/consumer/dedupe"
	"github.com/power-finance/kafka-client-go/envelope"
	"github.com/power-finance/kafka-client-go/publisher"
	"github.com/twmb/franz-go/pkg/kgo"

	"services/webhook-service/internal/health"
	"services/webhook-service/webhook_service/types"
)

// EventHandler is what the consumer hands each decoded outbox event to.
type EventHandler interface {
	Handle(ctx context.Context, event types.OutboxEvent) error
}

// Consumer drains the outbox topics into an EventHandler.
type Consumer struct {
	client            *kgo.Client
	messageHandler    *consumer.MessageHandler
	retryDLQPublisher *publisher.KafkaPublisher
	readinessProbe    *health.Probe
}

// NewConsumer wires a consumer-group client, dedupe store and retry/DLQ publishers around the supplied event handler.
func NewConsumer(
	ctx context.Context,
	kafkaConfig Config,
	dedupeStore dedupe.Store,
	eventHandler EventHandler,
	readinessProbe *health.Probe,
) (*Consumer, error) {
	groupClient, clientErr := kgo.NewClient(
		kgo.SeedBrokers(strings.Split(kafkaConfig.BootstrapServers, ",")...),
		kgo.ClientID(clientID),
		kgo.ConsumerGroup(kafkaConfig.GroupID),
		kgo.ConsumeTopics(kafkaConfig.OutboxTopics...),
		kgo.FetchIsolationLevel(kgo.ReadCommitted()),
		kgo.DisableAutoCommit(),
	)
	if clientErr != nil {
		return nil, fmt.Errorf("kafka: consumer-group client: %w", clientErr)
	}

	if pingErr := groupClient.Ping(ctx); pingErr != nil {
		groupClient.Close()
		return nil, fmt.Errorf("kafka: broker unreachable: %w", pingErr)
	}

	retryDLQPublisher := publisher.NewKafkaPublisher(
		publisher.DefaultProducerConfig(kafkaConfig.BootstrapServers),
	)
	if startErr := retryDLQPublisher.Start(ctx); startErr != nil {
		groupClient.Close()
		return nil, fmt.Errorf("kafka: retry/dlq publisher: %w", startErr)
	}

	decodeAndHandle := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		return eventHandler.Handle(ctx, OutboxEventFromMessage(message))
	}

	messageHandler := consumer.NewMessageHandler(
		decodeAndHandle,
		consumer.MessageHandlerConfig{
			Policy:         consumer.DefaultRetryPolicy(),
			RetryPublisher: publisher.NewRetryPublisher(retryDLQPublisher, kafkaConfig.RetryTopic),
			DLQPublisher:   publisher.NewDLQPublisher(retryDLQPublisher, kafkaConfig.DLQTopic),
			DedupeStore:    dedupeStore,
			EventID:        extractEventID,
			Logger:         slog.Default(),
		},
	)

	return &Consumer{
		client:            groupClient,
		messageHandler:    messageHandler,
		retryDLQPublisher: retryDLQPublisher,
		readinessProbe:    readinessProbe,
	}, nil
}

// Run drains the consumer group, committing each record only after it has been handled (or terminally routed).
func (c *Consumer) Run(ctx context.Context) {
	c.readinessProbe.MarkReady()
	defer c.readinessProbe.MarkUnready()
	logConsumerStarted()

	for {
		fetches := c.client.PollFetches(ctx)
		if ctx.Err() != nil || fetches.IsClientClosed() {
			logConsumerStopped()
			return
		}

		c.logFetchErrors(fetches)
		fetches.EachRecord(func(record *kgo.Record) {
			if ctx.Err() != nil {
				return
			}
			c.processRecord(ctx, record)
		})
	}
}

// Close releases the consumer-group client and the retry/DLQ publisher, flushing any buffered retry/DLQ records.
func (c *Consumer) Close() {
	c.retryDLQPublisher.Stop()
	c.client.Close()
}

func (c *Consumer) processRecord(ctx context.Context, record *kgo.Record) {
	message := consumer.MessageFromRecord(record)

	if handleErr := c.messageHandler.Handle(ctx, message); handleErr != nil {
		if errors.Is(handleErr, context.Canceled) {
			return
		}
		logHandlerFailed(handleErr)
		return
	}

	if commitErr := c.client.CommitRecords(ctx, record); commitErr != nil && ctx.Err() == nil {
		logCommitFailed(record.Topic, record.Partition, record.Offset, commitErr)
	}
}

func (c *Consumer) logFetchErrors(fetches kgo.Fetches) {
	fetches.EachError(func(topic string, partition int32, fetchErr error) {
		if errors.Is(fetchErr, context.Canceled) {
			return
		}

		logFetchFailed(topic, partition, fetchErr)
	})
}

func extractEventID(message kafkaclient.ConsumedMessage) (string, bool) {
	return headerValue(message, envelope.EventID)
}
