package consumer

import (
	"github.com/twmb/franz-go/pkg/kgo"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/headers"
)

func MessageFromRecord(record *kgo.Record) kafkaclient.ConsumedMessage {
	recordHeaders := make(headers.KafkaHeaders, len(record.Headers))
	for i, header := range record.Headers {
		recordHeaders[i] = headers.Header{Key: header.Key, Value: header.Value}
	}

	return kafkaclient.ConsumedMessage{
		Topic:     record.Topic,
		Partition: record.Partition,
		Offset:    record.Offset,
		Key:       record.Key,
		Value:     record.Value,
		Headers:   recordHeaders,
	}
}
