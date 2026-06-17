package consumer

import (
	"testing"

	"github.com/twmb/franz-go/pkg/kgo"

	"github.com/power-finance/kafka-client-go/headers"
)

func TestMessageFromRecordCopiesAllFields(t *testing.T) {
	record := &kgo.Record{
		Topic:     "events.async",
		Partition: 7,
		Offset:    4242,
		Key:       []byte("acct-1"),
		Value:     []byte("payload"),
		Headers: []kgo.RecordHeader{
			{Key: "event_id", Value: []byte("evt-1")},
			{Key: "x-correlation-id", Value: []byte("corr-1")},
		},
	}

	message := MessageFromRecord(record)

	if message.Topic != "events.async" {
		t.Fatalf("expected topic events.async, got %q", message.Topic)
	}
	if message.Partition != 7 || message.Offset != 4242 {
		t.Fatalf("expected partition/offset 7/4242, got %d/%d", message.Partition, message.Offset)
	}
	if string(message.Key) != "acct-1" || string(message.Value) != "payload" {
		t.Fatalf("expected key/value passthrough, got %q/%q", message.Key, message.Value)
	}
	if eventID, _ := headers.Get(message.Headers, "event_id"); eventID != "evt-1" {
		t.Fatalf("expected event_id header evt-1, got %q", eventID)
	}
	if correlationID, _ := headers.Get(message.Headers, "x-correlation-id"); correlationID != "corr-1" {
		t.Fatalf("expected correlation header corr-1, got %q", correlationID)
	}
}

func TestMessageFromRecordWithoutHeaders(t *testing.T) {
	message := MessageFromRecord(&kgo.Record{Topic: "events.async"})

	if len(message.Headers) != 0 {
		t.Fatalf("expected no headers, got %d", len(message.Headers))
	}
}
