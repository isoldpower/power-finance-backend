package consumer

import (
	"errors"
	"fmt"
	"testing"
	"time"

	kafkaclient "github.com/power-finance/kafka-client-go"
)

func TestPoisonIsNeverRetryable(t *testing.T) {
	policy := DefaultRetryPolicy()

	if policy.IsRetryable(kafkaclient.ErrPoison) {
		t.Fatal("poison must never be retryable")
	}
	if policy.IsRetryable(fmt.Errorf("%w: bad payload", kafkaclient.ErrPoison)) {
		t.Fatal("wrapped poison must never be retryable")
	}
}

func TestTransientIsAlwaysRetryable(t *testing.T) {
	policy := DefaultRetryPolicy()

	if !policy.IsRetryable(kafkaclient.ErrTransient) {
		t.Fatal("transient must be retryable")
	}
	if !policy.IsRetryable(fmt.Errorf("%w: blip", kafkaclient.ErrTransient)) {
		t.Fatal("wrapped transient must be retryable")
	}
}

func TestCustomRetryableTargets(t *testing.T) {
	errConnectionReset := errors.New("connection reset")
	policy := DefaultRetryPolicy()
	policy.Retryable = []error{errConnectionReset}

	if !policy.IsRetryable(fmt.Errorf("publish failed: %w", errConnectionReset)) {
		t.Fatal("configured target must be retryable")
	}
	if policy.IsRetryable(errors.New("unrelated")) {
		t.Fatal("unconfigured error must not be retryable")
	}
}

func TestRetryableFuncClassifiesUnknownErrors(t *testing.T) {
	policy := DefaultRetryPolicy()
	policy.RetryableFunc = func(err error) bool {
		return err.Error() == "flaky"
	}

	if !policy.IsRetryable(errors.New("flaky")) {
		t.Fatal("predicate match must be retryable")
	}
	if policy.IsRetryable(errors.New("fatal")) {
		t.Fatal("predicate miss must not be retryable")
	}
}

func TestComputeBackoffGrowsExponentially(t *testing.T) {
	policy := DefaultRetryPolicy()
	policy.JitterRatio = 0

	expectations := map[int]time.Duration{
		1: 1 * time.Second,
		2: 2 * time.Second,
		3: 4 * time.Second,
		4: 8 * time.Second,
	}
	for attempt, expected := range expectations {
		if got := policy.ComputeBackoff(attempt); got != expected {
			t.Fatalf("attempt %d: expected %v, got %v", attempt, expected, got)
		}
	}
}

func TestComputeBackoffIsCappedAtMaxBackoff(t *testing.T) {
	policy := DefaultRetryPolicy()
	policy.JitterRatio = 0
	policy.MaxBackoff = 5 * time.Second

	if got := policy.ComputeBackoff(10); got != 5*time.Second {
		t.Fatalf("expected cap at 5s, got %v", got)
	}
}

func TestComputeBackoffClampsAttemptBelowOne(t *testing.T) {
	policy := DefaultRetryPolicy()
	policy.JitterRatio = 0

	if got := policy.ComputeBackoff(0); got != policy.ComputeBackoff(1) {
		t.Fatalf("attempt below 1 must behave like attempt 1, got %v", got)
	}
}

func TestComputeBackoffJitterStaysWithinBounds(t *testing.T) {
	policy := DefaultRetryPolicy()
	policy.JitterRatio = 0.2

	lowerBound := 800 * time.Millisecond
	upperBound := 1200 * time.Millisecond
	for range 200 {
		backoff := policy.ComputeBackoff(1)
		if backoff < lowerBound || backoff > upperBound {
			t.Fatalf("jittered backoff %v outside [%v, %v]", backoff, lowerBound, upperBound)
		}
	}
}

func TestComputeRetryAtAddsBackoffToNow(t *testing.T) {
	policy := DefaultRetryPolicy()
	policy.JitterRatio = 0
	now := time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)

	retryAt := policy.ComputeRetryAt(2, now)

	if expected := now.Add(2 * time.Second); !retryAt.Equal(expected) {
		t.Fatalf("expected %v, got %v", expected, retryAt)
	}
}
