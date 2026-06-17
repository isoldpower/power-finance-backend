package kafka

import (
	"bytes"
	"testing"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/envelope"
	"github.com/power-finance/kafka-client-go/headers"
)

func TestOutboxEventFromMessageMapsHeadersKeyAndValue(t *testing.T) {
	value := []byte(`{"user_id":7}`)
	message := kafkaclient.ConsumedMessage{
		Key:   []byte("clerk_7"),
		Value: value,
		Headers: headers.KafkaHeaders{
			headers.String(envelope.EventID, "evt-1"),
			headers.String(envelope.EventType, "TransactionCreated"),
			headers.String(envelope.AggregateType, "transaction"),
		},
	}

	event := OutboxEventFromMessage(message)

	if event.EventID != "evt-1" {
		t.Errorf("event id = %q, want evt-1", event.EventID)
	}
	if event.EventType != "TransactionCreated" {
		t.Errorf("event type = %q", event.EventType)
	}
	if event.AggregateType != "transaction" {
		t.Errorf("aggregate type = %q", event.AggregateType)
	}
	if event.UserExternalID != "clerk_7" {
		t.Errorf("user external id should come from the message key, got %q", event.UserExternalID)
	}
	if !bytes.Equal(event.Payload, value) {
		t.Errorf("payload should be the raw message value")
	}
}

func TestOutboxEventFromMessageToleratesMissingHeaders(t *testing.T) {
	event := OutboxEventFromMessage(kafkaclient.ConsumedMessage{Key: []byte("clerk_1")})

	if event.EventID != "" || event.EventType != "" || event.AggregateType != "" {
		t.Errorf("missing headers should map to empty strings, got %+v", event)
	}
	if event.UserExternalID != "clerk_1" {
		t.Errorf("user external id = %q, want clerk_1", event.UserExternalID)
	}
}
