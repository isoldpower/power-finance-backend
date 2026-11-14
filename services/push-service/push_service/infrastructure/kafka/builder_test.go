package kafka

import (
	"context"
	"errors"
	"testing"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/envelope"
	"github.com/power-finance/kafka-client-go/headers"
	"github.com/power-finance/observability-go/propagation"
	"github.com/power-finance/observability-go/sandbox"
	"github.com/power-finance/observability-go/tracing"

	"services/push-service/internal/health"
	"services/push-service/push_service/types"
)

func outboxKafkaMessage() kafkaclient.ConsumedMessage {
	return kafkaclient.ConsumedMessage{
		Topic: "events.async",
		Key:   []byte("user_2abc"),
		Value: []byte(`{"wallet_id":"wallet-1"}`),
		Headers: headers.KafkaHeaders{
			headers.String(envelope.EventID, "evt-1"),
			headers.String(envelope.EventType, "WalletCreated"),
			headers.String(envelope.AggregateType, "wallet"),
		},
	}
}

func TestEventsSinkHandlerDeliversOutboxEvent(t *testing.T) {
	eventsSink := make(chan types.OutboxEvent, 1)
	sinkHandler := newEventsSinkHandler(eventsSink)

	err := sinkHandler(context.Background(), outboxKafkaMessage())

	if err != nil {
		t.Fatal(err)
	}
	delivered := <-eventsSink
	if delivered.EventID != "evt-1" || delivered.EventType != "WalletCreated" {
		t.Fatalf("expected envelope headers to be extracted, got %+v", delivered)
	}
	if delivered.AggregateType != "wallet" || delivered.UserID != "user_2abc" {
		t.Fatalf("expected aggregate type and partition-key user id, got %+v", delivered)
	}
	if string(delivered.Payload) != `{"wallet_id":"wallet-1"}` {
		t.Fatalf("expected payload passthrough, got %q", delivered.Payload)
	}
}

func TestEventsSinkHandlerAbortsWhenContextCancelled(t *testing.T) {
	blockedSink := make(chan types.OutboxEvent)
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
	}, "")

	if event.EventID != "" || event.EventType != "" || event.AggregateType != "" {
		t.Fatalf("expected empty envelope metadata, got %+v", event)
	}
	if event.UserID != "" {
		t.Fatalf("expected empty user id for nil key, got %q", event.UserID)
	}
}

func TestBuildFailsFastWhenBrokerUnreachable(t *testing.T) {
	cancelledContext, cancel := context.WithCancel(context.Background())
	cancel()

	kafkaConfig := types.KafkaConfig{
		BootstrapServers: "localhost:1",
		OutboxTopics:     []string{"events.async"},
	}

	_, err := BuildNotificationsConsumerLoop(
		cancelledContext,
		kafkaConfig,
		make(chan types.OutboxEvent),
		health.NewProbe(),
	)

	if err == nil {
		t.Fatal("expected build to fail when the broker is unreachable")
	}
}

func installSandboxPropagation(t *testing.T) {
	t.Helper()
	t.Setenv(tracing.EnvironmentVariableSDKDisabled, "true")
	if _, _, configureErr := tracing.Configure(context.Background(), "push-service-test"); configureErr != nil {
		t.Fatal(configureErr)
	}
}

func sandboxTaggedKafkaMessage(sandboxID string) kafkaclient.ConsumedMessage {
	message := outboxKafkaMessage()
	message.Headers = append(
		message.Headers,
		propagation.InjectIntoKafkaHeaders(sandbox.AttachID(context.Background(), sandboxID))...,
	)
	return message
}

func TestBaselineForwardsSandboxTaggedEventsWithTheirSandbox(t *testing.T) {
	installSandboxPropagation(t)
	t.Setenv(sandbox.EnvironmentVariableID, "")
	eventsSink := make(chan types.OutboxEvent, 1)
	sinkHandler := newEventsSinkHandler(eventsSink)

	if handleErr := sinkHandler(context.Background(), sandboxTaggedKafkaMessage("nikita")); handleErr != nil {
		t.Fatal(handleErr)
	}

	select {
	case forwarded := <-eventsSink:
		if forwarded.SandboxID != "nikita" {
			t.Fatalf("expected the event to keep its sandbox, got %q", forwarded.SandboxID)
		}
	default:
		t.Fatal("expected the baseline to forward a sandbox-tagged event")
	}
}

func TestSandboxInstanceForwardsOnlyItsOwnEvents(t *testing.T) {
	installSandboxPropagation(t)
	t.Setenv(sandbox.EnvironmentVariableID, "nikita")
	eventsSink := make(chan types.OutboxEvent, 3)
	sinkHandler := newEventsSinkHandler(eventsSink)

	for _, message := range []kafkaclient.ConsumedMessage{
		outboxKafkaMessage(),
		sandboxTaggedKafkaMessage("anna"),
		sandboxTaggedKafkaMessage("nikita"),
	} {
		if handleErr := sinkHandler(context.Background(), message); handleErr != nil {
			t.Fatal(handleErr)
		}
	}

	if len(eventsSink) != 1 {
		t.Fatalf("expected only the sandbox's own event, got %d", len(eventsSink))
	}
	if forwarded := <-eventsSink; forwarded.SandboxID != "nikita" {
		t.Fatalf("expected the nikita event, got %q", forwarded.SandboxID)
	}
}
