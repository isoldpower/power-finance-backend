package consumer

import (
	"testing"
	"time"

	"github.com/power-finance/kafka-client-go/headers"
)

func TestRetryContextFromMessageWithoutHeaders(t *testing.T) {
	retryContext := RetryContextFromMessage(fakeMessage())

	if retryContext.RetryTopicAttemptsConsumed != 0 {
		t.Fatalf("expected 0 attempts consumed, got %d", retryContext.RetryTopicAttemptsConsumed)
	}
	if !retryContext.FirstFailedAt.IsZero() {
		t.Fatalf("expected zero FirstFailedAt, got %v", retryContext.FirstFailedAt)
	}
}

func TestRetryContextFromMessageReadsHeaders(t *testing.T) {
	firstFailedAt := time.Date(2026, 1, 1, 12, 0, 0, 0, time.UTC)
	message := fakeMessage()
	message.Headers = headers.KafkaHeaders{
		headers.Int(headers.RetryCount, 3),
		headers.Time(headers.FirstFailedAt, firstFailedAt),
	}

	retryContext := RetryContextFromMessage(message)

	if retryContext.RetryTopicAttemptsConsumed != 3 {
		t.Fatalf("expected 3 attempts consumed, got %d", retryContext.RetryTopicAttemptsConsumed)
	}
	if !retryContext.FirstFailedAt.Equal(firstFailedAt) {
		t.Fatalf("expected %v, got %v", firstFailedAt, retryContext.FirstFailedAt)
	}
}

func TestFirstFailedAtOrNowFallsBackToNow(t *testing.T) {
	before := time.Now().UTC()

	resolved := RetryContext{}.FirstFailedAtOrNow()

	after := time.Now().UTC()
	if resolved.Before(before) || resolved.After(after) {
		t.Fatalf("expected now-ish timestamp, got %v", resolved)
	}
}

func TestFirstFailedAtOrNowPreservesExistingValue(t *testing.T) {
	firstFailedAt := time.Date(2026, 1, 1, 12, 0, 0, 0, time.UTC)

	resolved := RetryContext{FirstFailedAt: firstFailedAt}.FirstFailedAtOrNow()

	if !resolved.Equal(firstFailedAt) {
		t.Fatalf("expected %v, got %v", firstFailedAt, resolved)
	}
}
