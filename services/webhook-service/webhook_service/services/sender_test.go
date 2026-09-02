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
	first := signPayload("secret", "1786553460", []byte(`{"event":"x"}`))
	second := signPayload("secret", "1786553460", []byte(`{"event":"x"}`))

	if first != second {
		t.Fatalf("signature not deterministic: %q != %q", first, second)
	}
	if first[:3] != "v1=" {
		t.Fatalf("signature missing v1 prefix: %q", first)
	}

	different := signPayload("other-secret", "1786553460", []byte(`{"event":"x"}`))
	if different == first {
		t.Fatalf("signature should differ for a different secret")
	}
}

// A replayed request must not stay verifiable forever, which only holds if the
// timestamp is inside the signed material rather than beside it.
func TestSignPayloadCoversTheTimestamp(t *testing.T) {
	body := []byte(`{"event":"x"}`)

	if signPayload("secret", "1786553460", body) == signPayload("secret", "1786553461", body) {
		t.Fatal("signature must change when the timestamp changes")
	}
}

func TestSendPostsSignedPayloadAndAccepts2xx(t *testing.T) {
	payload := []byte(`{"event":"transaction.created"}`)

	var gotSignature string
	var gotEvent string
	var gotTimestamp string
	var gotDelivery string
	var gotBody []byte
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		gotSignature = request.Header.Get(signatureHeader)
		gotEvent = request.Header.Get(eventTypeHeader)
		gotTimestamp = request.Header.Get(timestampHeader)
		gotDelivery = request.Header.Get(deliveryHeader)
		gotBody = make([]byte, request.ContentLength)
		_, _ = request.Body.Read(gotBody)
		writer.WriteHeader(http.StatusAccepted)
	}))
	defer server.Close()

	sender := NewHTTPSender(2*time.Second, WithAllowPrivateAddresses())
	delivery := types.Delivery{
		ID:        "delivery-1",
		EventID:   "evt_5f1c8b2a9d",
		EventType: "transaction.created",
		TargetURL: server.URL,
		Payload:   payload,
	}
	sentAt := time.Unix(1786553460, 0).UTC()

	if sendErr := sender.Send(context.Background(), delivery, "secret", sentAt); sendErr != nil {
		t.Fatalf("expected success on 2xx, got %v", sendErr)
	}
	if gotTimestamp != "1786553460" {
		t.Fatalf("unexpected timestamp header: %q", gotTimestamp)
	}
	if gotDelivery != "evt_5f1c8b2a9d" {
		t.Fatalf("delivery header must carry the event id, got %q", gotDelivery)
	}
	if gotSignature != signPayload("secret", "1786553460", payload) {
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

	sender := NewHTTPSender(2*time.Second, WithAllowPrivateAddresses())
	delivery := types.Delivery{
		ID:        "delivery-1",
		EventType: "transaction.created",
		TargetURL: server.URL,
		Payload:   []byte("{}"),
	}

	if sendErr := sender.Send(context.Background(), delivery, "secret", time.Now().UTC()); sendErr == nil {
		t.Fatalf("expected error on non-2xx response")
	}
}

func TestSendBlocksLoopbackTargetBySSRFGuard(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, _ *http.Request) {
		writer.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	senderWithSSRFGuardActive := NewHTTPSender(2 * time.Second)
	delivery := types.Delivery{
		ID:        "delivery-1",
		EventType: "transaction.created",
		TargetURL: server.URL,
		Payload:   []byte("{}"),
	}

	if sendErr := senderWithSSRFGuardActive.Send(context.Background(), delivery, "secret", time.Now().UTC()); sendErr == nil {
		t.Fatalf("expected SSRF guard to block a loopback target")
	}
}

func TestSendRejectsNonHTTPScheme(t *testing.T) {
	sender := NewHTTPSender(2*time.Second, WithAllowPrivateAddresses())
	delivery := types.Delivery{
		ID:        "delivery-1",
		EventType: "transaction.created",
		TargetURL: "file:///etc/passwd",
		Payload:   []byte("{}"),
	}

	if sendErr := sender.Send(context.Background(), delivery, "secret", time.Now().UTC()); sendErr == nil {
		t.Fatalf("expected non-http(s) scheme to be rejected")
	}
}

func TestSendDoesNotFollowRedirects(t *testing.T) {
	var targetHits int
	target := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, _ *http.Request) {
		targetHits++
		writer.WriteHeader(http.StatusOK)
	}))
	defer target.Close()

	redirector := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		http.Redirect(writer, request, target.URL, http.StatusFound)
	}))
	defer redirector.Close()

	sender := NewHTTPSender(2*time.Second, WithAllowPrivateAddresses())
	delivery := types.Delivery{
		ID:        "delivery-1",
		EventType: "transaction.created",
		TargetURL: redirector.URL,
		Payload:   []byte("{}"),
	}

	if sendErr := sender.Send(context.Background(), delivery, "secret", time.Now().UTC()); sendErr == nil {
		t.Fatalf("expected redirect to be refused")
	}
	if targetHits != 0 {
		t.Fatalf("redirect target must not be followed, got %d hits", targetHits)
	}
}
