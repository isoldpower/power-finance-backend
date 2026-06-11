package consumer

import (
	"context"
	"time"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/headers"
	"github.com/power-finance/kafka-client-go/publisher"
)

type capturedPublish struct {
	topic   string
	key     []byte
	value   []byte
	headers headers.KafkaHeaders
}

type fakePublisher struct {
	published    []capturedPublish
	publishError error
}

func (f *fakePublisher) Publish(
	ctx context.Context,
	topic string,
	key []byte,
	value []byte,
	kafkaHeaders headers.KafkaHeaders,
) error {
	if f.publishError != nil {
		return f.publishError
	}
	f.published = append(f.published, capturedPublish{
		topic:   topic,
		key:     key,
		value:   value,
		headers: append(headers.KafkaHeaders(nil), kafkaHeaders...),
	})
	return nil
}

func fakeMessage() kafkaclient.ConsumedMessage {
	return kafkaclient.ConsumedMessage{
		Topic:     "events.async",
		Partition: 0,
		Offset:    0,
		Key:       []byte("acct-1"),
		Value:     []byte("payload"),
		Headers:   headers.KafkaHeaders{},
	}
}

func wireHandler(policy RetryPolicy, userHandler UserHandler) (*MessageHandler, *fakePublisher) {
	fake := &fakePublisher{}
	handler := NewMessageHandler(userHandler, MessageHandlerConfig{
		Policy:         policy,
		RetryPublisher: publisher.NewRetryPublisher(fake, "events.retry"),
		DLQPublisher:   publisher.NewDLQPublisher(fake, "events.dlq"),
	})
	handler.sleep = func(ctx context.Context, duration time.Duration) error { return nil }
	return handler, fake
}

func wireRouter(policy RetryPolicy) (*TerminalRouter, *fakePublisher) {
	fake := &fakePublisher{}
	router := NewTerminalRouter(
		policy,
		publisher.NewRetryPublisher(fake, "events.retry"),
		publisher.NewDLQPublisher(fake, "events.dlq"),
		nil,
	)
	return router, fake
}
