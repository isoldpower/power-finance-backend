package services

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"services/webhook-service/webhook_service/types"
)

func newAttempter(
	store *fakeDeliveryStore,
	secrets *fakeSecretResolver,
	sender *fakeSender,
	notifier *fakeNotifier,
	maxAttempts int,
) *DeliveryAttempter {
	return NewDeliveryAttempter(store, secrets, sender, notifier, maxAttempts, 30*time.Second)
}

func TestAttemptSuccessMarksSucceededAndNotifies(t *testing.T) {
	store := &fakeDeliveryStore{}
	notifier := &fakeNotifier{}
	attempter := newAttempter(store, &fakeSecretResolver{}, &fakeSender{}, notifier, 3)

	delivery := types.Delivery{ID: "d1", EventType: "transaction.created"}
	if err := attempter.Attempt(context.Background(), delivery, "secret"); err != nil {
		t.Fatalf("Attempt returned error: %v", err)
	}

	if len(store.succeeded) != 1 || store.succeeded[0] != "d1" {
		t.Fatalf("expected delivery marked succeeded, got %v", store.succeeded)
	}
	if len(store.rescheduled) != 0 || len(store.failed) != 0 {
		t.Fatalf("success path should not reschedule or fail")
	}
	if len(notifier.calls) != 1 || notifier.calls[0].short != "Webhook delivered" {
		t.Fatalf("expected success notification, got %+v", notifier.calls)
	}
}

func TestAttemptRetryableFailureReschedulesWithoutNotifying(t *testing.T) {
	store := &fakeDeliveryStore{}
	notifier := &fakeNotifier{}
	sender := &fakeSender{err: errors.New("connection refused")}
	attempter := newAttempter(store, &fakeSecretResolver{}, sender, notifier, 3)

	start := time.Now().UTC()
	delivery := types.Delivery{ID: "d1", Attempts: 0, EventType: "transaction.created"}
	if err := attempter.Attempt(context.Background(), delivery, "secret"); err != nil {
		t.Fatalf("Attempt returned error: %v", err)
	}

	if len(store.rescheduled) != 1 {
		t.Fatalf("expected one reschedule, got %d", len(store.rescheduled))
	}
	call := store.rescheduled[0]
	if call.attempts != 1 {
		t.Fatalf("expected attempts=1, got %d", call.attempts)
	}
	if !strings.Contains(call.lastError, "connection refused") {
		t.Fatalf("expected last error recorded, got %q", call.lastError)
	}
	if !call.nextAttemptAt.After(start) {
		t.Fatalf("next attempt should be in the future, got %v", call.nextAttemptAt)
	}
	if len(notifier.calls) != 0 {
		t.Fatalf("retryable failure should not notify, got %+v", notifier.calls)
	}
}

func TestAttemptExhaustionMarksFailedAndNotifies(t *testing.T) {
	store := &fakeDeliveryStore{}
	notifier := &fakeNotifier{}
	sender := &fakeSender{err: errors.New("boom")}
	attempter := newAttempter(store, &fakeSecretResolver{}, sender, notifier, 3)

	delivery := types.Delivery{ID: "d1", Attempts: 2, EventType: "transaction.created"}
	if err := attempter.Attempt(context.Background(), delivery, "secret"); err != nil {
		t.Fatalf("Attempt returned error: %v", err)
	}

	if len(store.failed) != 1 || store.failed[0] != "d1" {
		t.Fatalf("expected delivery marked failed, got %v", store.failed)
	}
	if len(store.rescheduled) != 0 {
		t.Fatalf("exhausted delivery should not reschedule")
	}
	if len(notifier.calls) != 1 || notifier.calls[0].short != "Webhook delivery failed" {
		t.Fatalf("expected failure notification, got %+v", notifier.calls)
	}
	if !strings.Contains(notifier.calls[0].message, "3 attempts") {
		t.Fatalf("failure notification should mention attempt count, got %q", notifier.calls[0].message)
	}
}

func TestAttemptResolvesEmptySecretFromStore(t *testing.T) {
	secrets := &fakeSecretResolver{secret: "resolved"}
	sender := &fakeSender{}
	attempter := newAttempter(&fakeDeliveryStore{}, secrets, sender, &fakeNotifier{}, 3)

	delivery := types.Delivery{ID: "d1", WebhookID: "wh1"}
	if err := attempter.Attempt(context.Background(), delivery, ""); err != nil {
		t.Fatalf("Attempt returned error: %v", err)
	}

	if secrets.calls != 1 {
		t.Fatalf("expected secret resolved once, got %d calls", secrets.calls)
	}
	if len(sender.secrets) != 1 || sender.secrets[0] != "resolved" {
		t.Fatalf("expected resolved secret used for send, got %v", sender.secrets)
	}
}

func TestAttemptKeepsSuppliedSecret(t *testing.T) {
	secrets := &fakeSecretResolver{secret: "resolved"}
	sender := &fakeSender{}
	attempter := newAttempter(&fakeDeliveryStore{}, secrets, sender, &fakeNotifier{}, 3)

	delivery := types.Delivery{ID: "d1", WebhookID: "wh1"}
	if err := attempter.Attempt(context.Background(), delivery, "supplied"); err != nil {
		t.Fatalf("Attempt returned error: %v", err)
	}

	if secrets.calls != 0 {
		t.Fatalf("supplied secret should skip resolution, got %d calls", secrets.calls)
	}
	if sender.secrets[0] != "supplied" {
		t.Fatalf("expected supplied secret used, got %q", sender.secrets[0])
	}
}

func TestAttemptSecretResolutionFailureSkipsSend(t *testing.T) {
	secrets := &fakeSecretResolver{err: errors.New("store down")}
	sender := &fakeSender{}
	attempter := newAttempter(&fakeDeliveryStore{}, secrets, sender, &fakeNotifier{}, 3)

	err := attempter.Attempt(context.Background(), types.Delivery{ID: "d1"}, "")
	if err == nil {
		t.Fatalf("expected error when secret resolution fails")
	}
	if len(sender.deliveries) != 0 {
		t.Fatalf("send must not run without a secret")
	}
}

func TestAttemptNotificationFailureIsBestEffort(t *testing.T) {
	store := &fakeDeliveryStore{}
	notifier := &fakeNotifier{err: errors.New("kafka down")}
	attempter := newAttempter(store, &fakeSecretResolver{}, &fakeSender{}, notifier, 3)

	if err := attempter.Attempt(context.Background(), types.Delivery{ID: "d1"}, "secret"); err != nil {
		t.Fatalf("notification failure must not fail the delivery outcome, got %v", err)
	}
	if len(store.succeeded) != 1 {
		t.Fatalf("delivery should still be marked succeeded")
	}
}
