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
	"go.opentelemetry.io/otel"
	otelpropagation "go.opentelemetry.io/otel/propagation"

	"services/webhook-service/webhook_service/types"
)

func init() {
	otel.SetTextMapPropagator(otelpropagation.NewCompositeTextMapPropagator(
		otelpropagation.TraceContext{},
		otelpropagation.Baggage{},
	))
}

type recordingEventHandler struct {
	handled     []types.OutboxEvent
	returnErr   error
	callCount   int
	lastContext context.Context
}

func (h *recordingEventHandler) Handle(ctx context.Context, event types.OutboxEvent) error {
	h.callCount++
	h.handled = append(h.handled, event)
	h.lastContext = ctx

	return h.returnErr
}

func outboxMessage(extraHeaders ...headers.Header) kafkaclient.ConsumedMessage {
	messageHeaders := headers.KafkaHeaders{
		headers.String(envelope.EventID, "evt-1"),
		headers.String(envelope.EventType, "WebhookEndpointCreated"),
		headers.String(envelope.AggregateType, "webhook"),
	}
	messageHeaders = append(messageHeaders, extraHeaders...)

	return kafkaclient.ConsumedMessage{
		Topic:   "events.async",
		Key:     []byte("user_2abc"),
		Value:   []byte(`{"webhook_id":"webhook-1"}`),
		Headers: messageHeaders,
	}
}

func sandboxBaggageHeader(t *testing.T, sandboxID string) headers.Header {
	t.Helper()

	injected := propagation.InjectIntoKafkaHeaders(
		sandbox.AttachID(context.Background(), sandboxID),
	)
	for _, header := range injected {
		if header.Key == "baggage" {
			return header
		}
	}
	t.Fatalf("no baggage header produced for %q", sandboxID)

	return headers.Header{}
}

func TestBaselineConsumerHandlesUntaggedTraffic(t *testing.T) {
	t.Setenv(sandbox.EnvironmentVariableID, "")
	eventHandler := &recordingEventHandler{}

	err := newOutboxEventHandler(eventHandler)(context.Background(), outboxMessage())

	if err != nil {
		t.Fatal(err)
	}
	if eventHandler.callCount != 1 {
		t.Fatalf("expected the event to be handled once, got %d", eventHandler.callCount)
	}
	handled := eventHandler.handled[0]
	if handled.EventID != "evt-1" || handled.EventType != "WebhookEndpointCreated" {
		t.Fatalf("expected the envelope headers to be decoded, got %+v", handled)
	}
}

func TestBaselineConsumerSkipsASandboxsTraffic(t *testing.T) {
	t.Setenv(sandbox.EnvironmentVariableID, "")
	eventHandler := &recordingEventHandler{}

	err := newOutboxEventHandler(eventHandler)(
		context.Background(),
		outboxMessage(sandboxBaggageHeader(t, "nikita")),
	)

	if err != nil {
		t.Fatalf("a skipped message must not be an error, got %v", err)
	}
	if eventHandler.callCount != 0 {
		t.Fatalf("expected the sandbox message to be skipped, handled %d", eventHandler.callCount)
	}
}

func TestSandboxConsumerHandlesOnlyItsOwnTraffic(t *testing.T) {
	t.Setenv(sandbox.EnvironmentVariableID, "nikita")
	eventHandler := &recordingEventHandler{}
	handle := newOutboxEventHandler(eventHandler)

	if err := handle(context.Background(), outboxMessage(sandboxBaggageHeader(t, "nikita"))); err != nil {
		t.Fatal(err)
	}
	if eventHandler.callCount != 1 {
		t.Fatalf("expected the sandbox to handle its own message, got %d", eventHandler.callCount)
	}

	if err := handle(context.Background(), outboxMessage(sandboxBaggageHeader(t, "anna"))); err != nil {
		t.Fatal(err)
	}
	if err := handle(context.Background(), outboxMessage()); err != nil {
		t.Fatal(err)
	}
	if eventHandler.callCount != 1 {
		t.Fatalf("expected foreign and baseline traffic to be skipped, handled %d", eventHandler.callCount)
	}
}

func TestHandlerErrorIsPropagatedForRetry(t *testing.T) {
	t.Setenv(sandbox.EnvironmentVariableID, "")
	handlerErr := errors.New("delivery store unreachable")
	eventHandler := &recordingEventHandler{returnErr: handlerErr}

	err := newOutboxEventHandler(eventHandler)(context.Background(), outboxMessage())

	if !errors.Is(err, handlerErr) {
		t.Fatalf("expected the handler error to reach the retry machinery, got %v", err)
	}
}

func TestConsumerSpanIsStartedForAHandledMessage(t *testing.T) {
	t.Setenv(sandbox.EnvironmentVariableID, "")
	eventHandler := &recordingEventHandler{}

	if err := newOutboxEventHandler(eventHandler)(context.Background(), outboxMessage()); err != nil {
		t.Fatal(err)
	}

	if eventHandler.lastContext == nil {
		t.Fatal("expected the handler to be called with a context")
	}
}

func TestExtractEventIDReadsTheEnvelopeHeader(t *testing.T) {
	eventID, isFound := extractEventID(outboxMessage())
	if !isFound || eventID != "evt-1" {
		t.Fatalf("expected evt-1, got %q found=%v", eventID, isFound)
	}

	if _, isFound := extractEventID(kafkaclient.ConsumedMessage{}); isFound {
		t.Fatal("expected no event id on a message without envelope headers")
	}
}
