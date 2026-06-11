package kafka

import (
	"context"
	"errors"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/consumer"
	"github.com/twmb/franz-go/pkg/kgo"

	"services/push-service/internal/log"
)

type groupConsumer interface {
	PollFetches(ctx context.Context) kgo.Fetches
	CommitRecords(ctx context.Context, records ...*kgo.Record) error
	Close()
}

type messageHandler interface {
	Handle(ctx context.Context, message kafkaclient.ConsumedMessage) error
}

type ConsumerLoop struct {
	consumer groupConsumer
	handler  messageHandler
}

func NewConsumerLoop(consumer groupConsumer, handler messageHandler) *ConsumerLoop {
	return &ConsumerLoop{consumer: consumer, handler: handler}
}

func (cl *ConsumerLoop) Run(ctx context.Context) {
	defer cl.consumer.Close()
	log.Successln("Kafka consumer started")

	for {
		fetches := cl.consumer.PollFetches(ctx)
		if ctx.Err() != nil || fetches.IsClientClosed() {
			log.Infoln("Kafka consumer stopped")
			return
		}

		cl.logFetchErrors(fetches)
		for _, record := range fetches.Records() {
			if ctx.Err() != nil {
				log.Infoln("Kafka consumer stopped mid-batch")
				return
			}

			cl.processRecord(ctx, record)
		}
	}
}

func (cl *ConsumerLoop) processRecord(ctx context.Context, record *kgo.Record) {
	message := consumer.MessageFromRecord(record)

	if handleErr := cl.handler.Handle(ctx, message); handleErr != nil {
		log.PrintError(
			"Kafka handler failed; offset not committed, message will be redelivered",
			handleErr,
		)
		return
	}

	if commitErr := cl.consumer.CommitRecords(ctx, record); commitErr != nil {
		log.PrintError("Failed to commit Kafka offset", commitErr)
	}
}

func (cl *ConsumerLoop) logFetchErrors(fetches kgo.Fetches) {
	fetches.EachError(func(topic string, partition int32, fetchErr error) {
		if errors.Is(fetchErr, context.Canceled) {
			return
		}

		log.Errorln("Kafka fetch error topic=%s partition=%d: %v", topic, partition, fetchErr)
	})
}
