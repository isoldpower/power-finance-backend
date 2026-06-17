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

func TestSchedulerWakeIsNonBlockingAndCoalesces(t *testing.T) {
	scheduler := NewRetryScheduler(&fakeDeliveryStore{}, &fakeAttempter{}, time.Hour)

	const moreWakesThanBufferCapacity = 5
	for i := 0; i < moreWakesThanBufferCapacity; i++ {
		scheduler.Wake()
	}

	select {
	case <-scheduler.wake:
	default:
		t.Fatal("expected one buffered wake")
	}
	select {
	case <-scheduler.wake:
		t.Fatal("wakes should coalesce to a single buffered signal")
	default:
	}
}

func TestSchedulerRunAttemptsOnWake(t *testing.T) {
	store := &fakeDeliveryStore{claimDue: []types.Delivery{{ID: "d1"}}}
	attempter := &signalingAttempter{attempted: make(chan types.Delivery, 1)}
	intervalTooLongToTickDuringTest := time.Hour
	scheduler := NewRetryScheduler(store, attempter, intervalTooLongToTickDuringTest)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go scheduler.Run(ctx)

	scheduler.Wake()

	select {
	case delivery := <-attempter.attempted:
		if delivery.ID != "d1" {
			t.Fatalf("unexpected delivery attempted: %q", delivery.ID)
		}
	case <-time.After(time.Second):
		t.Fatal("expected wake to trigger a delivery attempt")
	}
}
