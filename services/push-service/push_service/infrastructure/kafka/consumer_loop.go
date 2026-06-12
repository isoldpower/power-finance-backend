package kafka

import (
	"context"
	"errors"
	"log/slog"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/consumer"
	"github.com/twmb/franz-go/pkg/kgo"

	"services/push-service/internal/health"
)

type broadcastConsumer interface {
	PollFetches(ctx context.Context) kgo.Fetches
	Close()
}

type MessageHandlerFunc func(ctx context.Context, message kafkaclient.ConsumedMessage) error

// ConsumerLoop drains a groupless broadcast consumer.
// No commits, selected at-most-once delivery strategy.
type ConsumerLoop struct {
	consumer       broadcastConsumer
	handle         MessageHandlerFunc
	readinessProbe *health.Probe
}

func NewConsumerLoop(
	consumer broadcastConsumer,
	handle MessageHandlerFunc,
	readinessProbe *health.Probe,
) *ConsumerLoop {
	return &ConsumerLoop{
		consumer:       consumer,
		handle:         handle,
		readinessProbe: readinessProbe,
	}
}

func (cl *ConsumerLoop) Run(ctx context.Context) {
	defer cl.consumer.Close()
	cl.readinessProbe.MarkReady()
	defer cl.readinessProbe.MarkUnready()
	slog.Info("kafka consumer started")

	for {
		fetches := cl.consumer.PollFetches(ctx)
		if ctx.Err() != nil || fetches.IsClientClosed() {
			slog.Info("kafka consumer stopped")
			return
		}

		cl.logFetchErrors(fetches)
		for _, record := range fetches.Records() {
			if ctx.Err() != nil {
				slog.Info("kafka consumer stopped mid-batch")
				return
			}

			cl.processRecord(ctx, record)
		}
	}
}

func (cl *ConsumerLoop) processRecord(ctx context.Context, record *kgo.Record) {
	message := consumer.MessageFromRecord(record)

	if handleErr := cl.handle(ctx, message); handleErr != nil && !errors.Is(handleErr, context.Canceled) {
		slog.Error("kafka handler failed, event dropped", "error", handleErr)
	}
}

func (cl *ConsumerLoop) logFetchErrors(fetches kgo.Fetches) {
	fetches.EachError(func(topic string, partition int32, fetchErr error) {
		if errors.Is(fetchErr, context.Canceled) {
			return
		}

		slog.Error(
			"kafka fetch error",
			"topic", topic,
			"partition", partition,
			"error", fetchErr,
		)
	})
}
