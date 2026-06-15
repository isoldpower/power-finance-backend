package services

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"services/webhook-service/webhook_service/types"
)

func TestSignPayloadIsDeterministicAndPrefixed(t *testing.T) {
	first := signPayload("secret", []byte(`{"event":"x"}`))
	second := signPayload("secret", []byte(`{"event":"x"}`))

	if first != second {
		t.Fatalf("signature not deterministic: %q != %q", first, second)
	}
	if first[:3] != "v1=" {
		t.Fatalf("signature missing v1 prefix: %q", first)
	}

	different := signPayload("other-secret", []byte(`{"event":"x"}`))
	if different == first {
		t.Fatalf("signature should differ for a different secret")
	}
}

func TestSendPostsSignedPayloadAndAccepts2xx(t *testing.T) {
	payload := []byte(`{"event":"transaction.created"}`)

	var gotSignature string
	var gotEvent string
	var gotBody []byte
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		gotSignature = request.Header.Get(signatureHeader)
		gotEvent = request.Header.Get(eventTypeHeader)
		gotBody = make([]byte, request.ContentLength)
		_, _ = request.Body.Read(gotBody)
		writer.WriteHeader(http.StatusAccepted)
	}))
	defer server.Close()

	sender := NewHTTPSender(2 * time.Second)
	delivery := types.Delivery{
		ID:        "delivery-1",
		EventType: "transaction.created",
		TargetURL: server.URL,
		Payload:   payload,
	}

	if sendErr := sender.Send(context.Background(), delivery, "secret"); sendErr != nil {
		t.Fatalf("expected success on 2xx, got %v", sendErr)
	}
	if gotSignature != signPayload("secret", payload) {
		t.Fatalf("unexpected signature header: %q", gotSignature)
	}
	if gotEvent != "transaction.created" {
		t.Fatalf("unexpected event header: %q", gotEvent)
	}
}

func TestSendReturnsErrorOnNon2xx(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, _ *http.Request) {
		writer.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	sender := NewHTTPSender(2 * time.Second)
	delivery := types.Delivery{
		ID:        "delivery-1",
		EventType: "transaction.created",
		TargetURL: server.URL,
		Payload:   []byte("{}"),
	}

	if sendErr := sender.Send(context.Background(), delivery, "secret"); sendErr == nil {
		t.Fatalf("expected error on non-2xx response")
	}
}
