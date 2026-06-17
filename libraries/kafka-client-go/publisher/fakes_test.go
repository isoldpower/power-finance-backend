package publisher

import (
	"context"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/headers"
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
