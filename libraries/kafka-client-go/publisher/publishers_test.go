package publisher

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/headers"
)

func TestRetryPublisherPublishesToConfiguredTopicWithKeyAndValue(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "events.retry")

	err := retryPublisher.Publish(context.Background(), fakeMessage(), RetryPublication{
		Error:       errors.New("blip"),
		NextRetryAt: time.Now().UTC(),
		Attempt:     1,
	})

	if err != nil {
		t.Fatal(err)
	}
	published := fake.published[0]
	if published.topic != "events.retry" {
		t.Fatalf("expected events.retry, got %q", published.topic)
	}
	if string(published.key) != "acct-1" || string(published.value) != "payload" {
		t.Fatalf("expected key/value passthrough, got %q/%q", published.key, published.value)
	}
}

func TestRetryPublisherDefaultTopic(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")

	err := retryPublisher.Publish(context.Background(), fakeMessage(), RetryPublication{
		Error:       errors.New("blip"),
		NextRetryAt: time.Now().UTC(),
		Attempt:     1,
	})

	if err != nil {
		t.Fatal(err)
	}
	if fake.published[0].topic != "events.retry" {
		t.Fatalf("expected default topic events.retry, got %q", fake.published[0].topic)
	}
}

func TestRetryPublisherCoercesNilValueToEmptyBytes(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")
	message := fakeMessage()
	message.Value = nil

	err := retryPublisher.Publish(context.Background(), message, RetryPublication{
		Error:       errors.New("blip"),
		NextRetryAt: time.Now().UTC(),
		Attempt:     1,
	})

	if err != nil {
		t.Fatal(err)
	}
	if published := fake.published[0]; published.value == nil || len(published.value) != 0 {
		t.Fatalf("expected empty bytes, got %v", published.value)
	}
}

func TestRetryPublisherOriginalTopicFallsBackToMessageTopic(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")

	err := retryPublisher.Publish(context.Background(), fakeMessage(), RetryPublication{
		Error:       errors.New("blip"),
		NextRetryAt: time.Now().UTC(),
		Attempt:     1,
	})

	if err != nil {
		t.Fatal(err)
	}
	if topic, _ := headers.Get(fake.published[0].headers, headers.OriginalTopic); topic != "events.async" {
		t.Fatalf("expected events.async, got %q", topic)
	}
}

func TestRetryPublisherPreservesOriginalTopicAcrossHops(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")
	inbound := fakeMessage()
	inbound.Topic = "events.retry"
	inbound.Headers = headers.KafkaHeaders{headers.String(headers.OriginalTopic, "events.async")}

	err := retryPublisher.Publish(context.Background(), inbound, RetryPublication{
		Error:       errors.New("blip"),
		NextRetryAt: time.Now().UTC(),
		Attempt:     2,
	})

	if err != nil {
		t.Fatal(err)
	}
	if topic, _ := headers.Get(fake.published[0].headers, headers.OriginalTopic); topic != "events.async" {
		t.Fatalf("expected preserved events.async, got %q", topic)
	}
}

func TestRetryPublisherStampsOriginalPartitionAndOffset(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")
	message := fakeMessage()
	message.Partition = 7
	message.Offset = 4242

	err := retryPublisher.Publish(context.Background(), message, RetryPublication{
		Error:       errors.New("blip"),
		NextRetryAt: time.Now().UTC(),
		Attempt:     1,
	})

	if err != nil {
		t.Fatal(err)
	}
	publishedHeaders := fake.published[0].headers
	if partition := headers.GetInt(publishedHeaders, headers.OriginalPartition, -1); partition != 7 {
		t.Fatalf("expected partition 7, got %d", partition)
	}
	if offset := headers.GetInt(publishedHeaders, headers.OriginalOffset, -1); offset != 4242 {
		t.Fatalf("expected offset 4242, got %d", offset)
	}
}

func TestRetryPublisherRecordsAttemptAndRetryAtVerbatim(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")
	nextRetryAt := time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)

	err := retryPublisher.Publish(context.Background(), fakeMessage(), RetryPublication{
		Error:       errors.New("blip"),
		NextRetryAt: nextRetryAt,
		Attempt:     42,
	})

	if err != nil {
		t.Fatal(err)
	}
	publishedHeaders := fake.published[0].headers
	if attempt := headers.GetInt(publishedHeaders, headers.RetryCount, -1); attempt != 42 {
		t.Fatalf("expected attempt 42, got %d", attempt)
	}
	if retryAt, _ := headers.GetTime(publishedHeaders, headers.RetryAt); !retryAt.Equal(nextRetryAt) {
		t.Fatalf("expected %v, got %v", nextRetryAt, retryAt)
	}
}

func TestRetryPublisherPreservesFirstFailedAtFromHeaders(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")
	journeyStart := time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)
	inbound := fakeMessage()
	inbound.Headers = headers.KafkaHeaders{headers.Time(headers.FirstFailedAt, journeyStart)}

	err := retryPublisher.Publish(context.Background(), inbound, RetryPublication{
		Error:       errors.New("blip"),
		NextRetryAt: time.Now().UTC(),
		Attempt:     2,
	})

	if err != nil {
		t.Fatal(err)
	}
	firstFailedAt, _ := headers.GetTime(fake.published[0].headers, headers.FirstFailedAt)
	if !firstFailedAt.Equal(journeyStart) {
		t.Fatalf("expected preserved %v, got %v", journeyStart, firstFailedAt)
	}
}

func TestRetryPublisherExplicitFirstFailedAtWinsOverHeaders(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")
	fromHeaders := time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)
	explicit := time.Date(2026, 2, 2, 0, 0, 0, 0, time.UTC)
	inbound := fakeMessage()
	inbound.Headers = headers.KafkaHeaders{headers.Time(headers.FirstFailedAt, fromHeaders)}

	err := retryPublisher.Publish(context.Background(), inbound, RetryPublication{
		Error:         errors.New("blip"),
		NextRetryAt:   time.Now().UTC(),
		Attempt:       2,
		FirstFailedAt: explicit,
	})

	if err != nil {
		t.Fatal(err)
	}
	firstFailedAt, _ := headers.GetTime(fake.published[0].headers, headers.FirstFailedAt)
	if !firstFailedAt.Equal(explicit) {
		t.Fatalf("expected explicit %v, got %v", explicit, firstFailedAt)
	}
}

func TestRetryPublisherPassesThroughCorrelationID(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")
	inbound := fakeMessage()
	inbound.Headers = headers.KafkaHeaders{headers.String(headers.CorrelationID, "corr-123")}

	err := retryPublisher.Publish(context.Background(), inbound, RetryPublication{
		Error:       errors.New("blip"),
		NextRetryAt: time.Now().UTC(),
		Attempt:     1,
	})

	if err != nil {
		t.Fatal(err)
	}
	correlationID, _ := headers.Get(fake.published[0].headers, headers.CorrelationID)
	if correlationID != "corr-123" {
		t.Fatalf("expected corr-123, got %q", correlationID)
	}
}

func TestRetryPublisherTruncatesLongErrorMessage(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")
	longError := errors.New(strings.Repeat("x", errorMessageMaxBytes+500))

	err := retryPublisher.Publish(context.Background(), fakeMessage(), RetryPublication{
		Error:       longError,
		NextRetryAt: time.Now().UTC(),
		Attempt:     1,
	})

	if err != nil {
		t.Fatal(err)
	}
	errorMessage, _ := headers.Get(fake.published[0].headers, headers.ErrorMessage)
	if len(errorMessage) != errorMessageMaxBytes {
		t.Fatalf("expected truncation to %d, got %d", errorMessageMaxBytes, len(errorMessage))
	}
}

func TestDLQPublisherDefaultTopicAndEnvelope(t *testing.T) {
	fake := &fakePublisher{}
	dlqPublisher := NewDLQPublisher(fake, "")
	firstFailedAt := time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)

	err := dlqPublisher.Publish(context.Background(), fakeMessage(), DLQPublication{
		Error:         errors.Join(kafkaclient.ErrTransient, errors.New("dead")),
		TotalAttempts: 8,
		FirstFailedAt: firstFailedAt,
	})

	if err != nil {
		t.Fatal(err)
	}
	published := fake.published[0]
	if published.topic != "events.dlq" {
		t.Fatalf("expected default topic events.dlq, got %q", published.topic)
	}
	if totalAttempts := headers.GetInt(published.headers, headers.RetryCount, -1); totalAttempts != 8 {
		t.Fatalf("expected total attempts 8, got %d", totalAttempts)
	}
	if class, _ := headers.Get(published.headers, headers.ErrorClass); class != "TransientError" {
		t.Fatalf("expected TransientError, got %q", class)
	}
	if stamped, _ := headers.GetTime(published.headers, headers.FirstFailedAt); !stamped.Equal(firstFailedAt) {
		t.Fatalf("expected %v, got %v", firstFailedAt, stamped)
	}
	if _, found := headers.GetTime(published.headers, headers.FailedAt); !found {
		t.Fatal("expected x-failed-at to be stamped")
	}
}

func TestRetryPublisherExplicitCorrelationIDOverridesHeader(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")
	inbound := fakeMessage()
	inbound.Headers = headers.KafkaHeaders{headers.String(headers.CorrelationID, "stale")}

	err := retryPublisher.Publish(context.Background(), inbound, RetryPublication{
		Error:         errors.New("blip"),
		NextRetryAt:   time.Now().UTC(),
		Attempt:       1,
		CorrelationID: "fresh",
	})

	if err != nil {
		t.Fatal(err)
	}
	correlationID, _ := headers.Get(fake.published[0].headers, headers.CorrelationID)
	if correlationID != "fresh" {
		t.Fatalf("expected explicit correlation id to win, got %q", correlationID)
	}
}

func TestRetryPublisherOmitsCorrelationIDWhenAbsent(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")

	err := retryPublisher.Publish(context.Background(), fakeMessage(), RetryPublication{
		Error:       errors.New("blip"),
		NextRetryAt: time.Now().UTC(),
		Attempt:     1,
	})

	if err != nil {
		t.Fatal(err)
	}
	if _, found := headers.Get(fake.published[0].headers, headers.CorrelationID); found {
		t.Fatal("expected correlation id header to be omitted when absent")
	}
}

func TestDLQPublisherPassesThroughCorrelationID(t *testing.T) {
	fake := &fakePublisher{}
	dlqPublisher := NewDLQPublisher(fake, "")
	inbound := fakeMessage()
	inbound.Headers = headers.KafkaHeaders{headers.String(headers.CorrelationID, "corr-dlq")}

	err := dlqPublisher.Publish(context.Background(), inbound, DLQPublication{
		Error:         errors.New("dead"),
		TotalAttempts: 4,
	})

	if err != nil {
		t.Fatal(err)
	}
	correlationID, _ := headers.Get(fake.published[0].headers, headers.CorrelationID)
	if correlationID != "corr-dlq" {
		t.Fatalf("expected corr-dlq, got %q", correlationID)
	}
}

func TestDLQPublisherPreservesOriginalTopicAcrossHops(t *testing.T) {
	fake := &fakePublisher{}
	dlqPublisher := NewDLQPublisher(fake, "")
	inbound := fakeMessage()
	inbound.Topic = "events.retry"
	inbound.Headers = headers.KafkaHeaders{headers.String(headers.OriginalTopic, "events.async")}

	err := dlqPublisher.Publish(context.Background(), inbound, DLQPublication{
		Error:         errors.New("dead"),
		TotalAttempts: 4,
	})

	if err != nil {
		t.Fatal(err)
	}
	if topic, _ := headers.Get(fake.published[0].headers, headers.OriginalTopic); topic != "events.async" {
		t.Fatalf("expected preserved events.async, got %q", topic)
	}
}

func TestEmptyOriginalTopicHeaderFallsBackToMessageTopic(t *testing.T) {
	fake := &fakePublisher{}
	retryPublisher := NewRetryPublisher(fake, "")
	inbound := fakeMessage()
	inbound.Headers = headers.KafkaHeaders{headers.String(headers.OriginalTopic, "")}

	err := retryPublisher.Publish(context.Background(), inbound, RetryPublication{
		Error:       errors.New("blip"),
		NextRetryAt: time.Now().UTC(),
		Attempt:     1,
	})

	if err != nil {
		t.Fatal(err)
	}
	if topic, _ := headers.Get(fake.published[0].headers, headers.OriginalTopic); topic != "events.async" {
		t.Fatalf("expected fallback to message topic, got %q", topic)
	}
}

func TestTruncateBoundaries(t *testing.T) {
	cases := map[string]struct {
		input    string
		maxBytes int
		expected string
	}{
		"shorter than budget": {input: "short", maxBytes: 10, expected: "short"},
		"exactly at budget":   {input: "1234567890", maxBytes: 10, expected: "1234567890"},
		"ascii over budget":   {input: "12345678901", maxBytes: 10, expected: "1234567890"},
		"multibyte at edge":   {input: strings.Repeat("é", 6), maxBytes: 5, expected: strings.Repeat("é", 2)},
	}
	for name, testCase := range cases {
		if got := truncate(testCase.input, testCase.maxBytes); got != testCase.expected {
			t.Fatalf("%s: expected %q, got %q", name, testCase.expected, got)
		}
	}
}
