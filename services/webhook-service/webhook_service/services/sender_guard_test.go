package services

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"services/webhook-service/webhook_service/types"
)

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

	sendErr := senderWithSSRFGuardActive.Send(context.Background(), delivery, "secret", time.Now().UTC())
	if sendErr == nil {
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
