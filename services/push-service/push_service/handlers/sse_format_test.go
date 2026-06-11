package handlers

import (
	"testing"

	"services/push-service/push_service/services"
)

func TestFormatServerSentEventFrame(t *testing.T) {
	frame := formatServerSentEvent(services.OutboxEvent{
		EventID:   "evt-1",
		EventType: "WalletCreated",
		Payload:   []byte(`{"wallet_id":"wallet-1"}`),
	})

	expected := "event: WalletCreated\n" +
		"id: evt-1\n" +
		"data: {\"wallet_id\":\"wallet-1\"}\n" +
		"\n"
	if string(frame) != expected {
		t.Fatalf("unexpected SSE frame:\n%q", frame)
	}
}

func TestFormatServerSentEventSplitsMultilinePayload(t *testing.T) {
	frame := formatServerSentEvent(services.OutboxEvent{
		EventType: "WalletCreated",
		Payload:   []byte("{\n  \"wallet_id\": \"wallet-1\"\n}"),
	})

	expected := "event: WalletCreated\n" +
		"data: {\n" +
		"data:   \"wallet_id\": \"wallet-1\"\n" +
		"data: }\n" +
		"\n"
	if string(frame) != expected {
		t.Fatalf("unexpected multiline SSE frame:\n%q", frame)
	}
}

func TestFormatServerSentEventOmitsIDWhenAbsent(t *testing.T) {
	frame := formatServerSentEvent(services.OutboxEvent{
		EventType: "WalletCreated",
		Payload:   []byte("{}"),
	})

	expected := "event: WalletCreated\n" +
		"data: {}\n" +
		"\n"
	if string(frame) != expected {
		t.Fatalf("unexpected SSE frame without id:\n%q", frame)
	}
}
