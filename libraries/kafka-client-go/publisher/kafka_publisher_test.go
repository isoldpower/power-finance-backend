package publisher

import (
	"context"
	"strings"
	"testing"

	"github.com/twmb/franz-go/pkg/kgo"

	"github.com/power-finance/kafka-client-go/headers"
	"github.com/power-finance/kafka-client-go/publisher/acknowledgement"
)

func TestPublishBeforeStartFails(t *testing.T) {
	kafkaPublisher := NewKafkaPublisher(DefaultProducerConfig("localhost:9092"))

	err := kafkaPublisher.Publish(
		context.Background(),
		"events.async",
		[]byte("key"),
		[]byte("value"),
		nil,
	)

	if err == nil {
		t.Fatal("expected publish before Start() to fail")
	}
	if !strings.Contains(err.Error(), "before Start") {
		t.Fatalf("expected actionable error message, got %q", err)
	}
}

func TestStopBeforeStartIsNoop(t *testing.T) {
	kafkaPublisher := NewKafkaPublisher(DefaultProducerConfig("localhost:9092"))

	kafkaPublisher.Stop()
}

func TestStartRejectsInvalidConfigWithoutConnecting(t *testing.T) {
	config := DefaultProducerConfig("localhost:9092")
	config.Acknowledgement = acknowledgement.AcknowledgeLeaderOnly

	err := NewKafkaPublisher(config).Start(context.Background())

	if err == nil {
		t.Fatal("expected invalid config to be rejected")
	}
}

func TestStartFailsWhenBrokerUnreachable(t *testing.T) {
	expiredContext, cancel := context.WithCancel(context.Background())
	cancel()

	kafkaPublisher := NewKafkaPublisher(DefaultProducerConfig("localhost:1"))
	err := kafkaPublisher.Start(expiredContext)

	if err == nil {
		t.Fatal("expected Start to fail when the broker is unreachable")
	}

	publishErr := kafkaPublisher.Publish(
		context.Background(),
		"events.async",
		nil,
		[]byte("value"),
		nil,
	)
	if publishErr == nil {
		t.Fatal("expected publisher to stay unusable after failed Start")
	}
}

func TestToRecordHeadersConvertsKeysAndValues(t *testing.T) {
	converted := toRecordHeaders(headers.KafkaHeaders{
		headers.String("a", "1"),
		headers.String("b", "2"),
	})

	expected := []kgo.RecordHeader{
		{Key: "a", Value: []byte("1")},
		{Key: "b", Value: []byte("2")},
	}
	if len(converted) != len(expected) {
		t.Fatalf("expected %d headers, got %d", len(expected), len(converted))
	}
	for i, header := range expected {
		if converted[i].Key != header.Key || string(converted[i].Value) != string(header.Value) {
			t.Fatalf("header %d: expected %+v, got %+v", i, header, converted[i])
		}
	}
}

func TestToRecordHeadersReturnsNilForEmptyInput(t *testing.T) {
	if converted := toRecordHeaders(nil); converted != nil {
		t.Fatalf("expected nil for empty headers, got %v", converted)
	}
}
