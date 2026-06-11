package kafka

import (
	"context"
	"errors"
	"testing"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/envelope"
	"github.com/power-finance/kafka-client-go/headers"

	"services/push-service/push_service/services"
)

func outboxKafkaMessage() kafkaclient.ConsumedMessage {
	return kafkaclient.ConsumedMessage{
		Topic: "events.async",
		Key:   []byte("wallet-1"),
		Value: []byte(`{"wallet_id":"wallet-1"}`),
		Headers: headers.KafkaHeaders{
			headers.String(envelope.EventID, "evt-1"),
			headers.String(envelope.EventType, "WalletCreated"),
			headers.String(envelope.AggregateType, "wallet"),
		},
	}
}

func TestEventsSinkHandlerDeliversOutboxEvent(t *testing.T) {
	eventsSink := make(chan services.OutboxEvent, 1)
	sinkHandler := newEventsSinkHandler(eventsSink)

	err := sinkHandler(context.Background(), outboxKafkaMessage())

	if err != nil {
		t.Fatal(err)
	}
	delivered := <-eventsSink
	if delivered.EventID != "evt-1" || delivered.EventType != "WalletCreated" {
		t.Fatalf("expected envelope headers to be extracted, got %+v", delivered)
	}
	if delivered.AggregateType != "wallet" || delivered.AggregateID != "wallet-1" {
		t.Fatalf("expected aggregate metadata, got %+v", delivered)
	}
	if string(delivered.Payload) != `{"wallet_id":"wallet-1"}` {
		t.Fatalf("expected payload passthrough, got %q", delivered.Payload)
	}
}

func TestEventsSinkHandlerAbortsWhenContextCancelled(t *testing.T) {
	blockedSink := make(chan services.OutboxEvent)
	sinkHandler := newEventsSinkHandler(blockedSink)
	cancelledContext, cancel := context.WithCancel(context.Background())
	cancel()

	err := sinkHandler(cancelledContext, outboxKafkaMessage())

	if !errors.Is(err, context.Canceled) {
		t.Fatalf("expected context.Canceled, got %v", err)
	}
}

func TestOutboxEventFromMessageWithoutHeaders(t *testing.T) {
	event := outboxEventFromMessage(kafkaclient.ConsumedMessage{
		Topic: "events.async",
		Value: []byte("payload"),
	})

	if event.EventID != "" || event.EventType != "" || event.AggregateType != "" {
		t.Fatalf("expected empty envelope metadata, got %+v", event)
	}
	if event.AggregateID != "" {
		t.Fatalf("expected empty aggregate id for nil key, got %q", event.AggregateID)
	}
}

func TestExtractEnvelopeEventID(t *testing.T) {
	message := kafkaclient.ConsumedMessage{
		Headers: headers.KafkaHeaders{headers.String(envelope.EventID, "evt-1")},
	}

	eventID, found := extractEnvelopeEventID(message)

	if !found || eventID != "evt-1" {
		t.Fatalf("expected evt-1, got %q/%v", eventID, found)
	}
}

func TestExtractEnvelopeEventIDMissing(t *testing.T) {
	if _, found := extractEnvelopeEventID(kafkaclient.ConsumedMessage{}); found {
		t.Fatal("expected missing event_id to report not found")
	}
}

func TestBuildFailsFastWhenBrokerUnreachable(t *testing.T) {
	cancelledContext, cancel := context.WithCancel(context.Background())
	cancel()

	config := LoadConsumerConfigFromEnv()
	config.BootstrapServers = "localhost:1"

	_, err := BuildNotificationsConsumerLoop(
		cancelledContext,
		config,
		make(chan services.OutboxEvent),
	)

	if err == nil {
		t.Fatal("expected build to fail when the broker is unreachable")
	}
}
