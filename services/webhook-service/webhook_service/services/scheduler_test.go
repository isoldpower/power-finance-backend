package services

import (
	"context"
	"errors"
	"testing"
	"time"

	"services/webhook-service/webhook_service/types"
)

func TestSchedulerAttemptsEveryClaimedDeliveryWithoutSecret(t *testing.T) {
	store := &fakeDeliveryStore{
		claimDue: []types.Delivery{{ID: "d1"}, {ID: "d2"}},
	}
	attempter := &fakeAttempter{}
	scheduler := NewRetryScheduler(store, attempter, time.Minute)

	scheduler.runOnce(context.Background())

	if len(attempter.deliveries) != 2 {
		t.Fatalf("expected both claimed deliveries attempted, got %d", len(attempter.deliveries))
	}
	for i, secret := range attempter.secrets {
		if secret != "" {
			t.Fatalf("claimed redelivery %d should pass an empty secret, got %q", i, secret)
		}
	}
}

func TestSchedulerClaimFailureSkipsAttempts(t *testing.T) {
	store := &fakeDeliveryStore{claimErr: errors.New("db down")}
	attempter := &fakeAttempter{}
	scheduler := NewRetryScheduler(store, attempter, time.Minute)

	scheduler.runOnce(context.Background())

	if len(attempter.deliveries) != 0 {
		t.Fatalf("no deliveries should be attempted when claim fails")
	}
}
