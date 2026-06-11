package consumer

import (
	"context"
	"errors"
	"fmt"
	"testing"
	"time"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/consumer/dedupe"
	"github.com/power-finance/kafka-client-go/headers"
	"github.com/power-finance/kafka-client-go/publisher"
)

func TestSuccessPublishesNothing(t *testing.T) {
	calls := 0
	succeed := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		calls++
		return nil
	}
	handler, fake := wireHandler(DefaultRetryPolicy(), succeed)

	if err := handler.Handle(context.Background(), fakeMessage()); err != nil {
		t.Fatal(err)
	}

	if calls != 1 {
		t.Fatalf("expected 1 call, got %d", calls)
	}
	if len(fake.published) != 0 {
		t.Fatalf("expected no publishes, got %d", len(fake.published))
	}
}

func TestPoisonRoutesToDLQImmediately(t *testing.T) {
	calls := 0
	poison := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		calls++
		return fmt.Errorf("%w: bad payload", kafkaclient.ErrPoison)
	}
	policy := DefaultRetryPolicy()
	policy.MaxInProcessAttempts = 3
	handler, fake := wireHandler(policy, poison)

	if err := handler.Handle(context.Background(), fakeMessage()); err != nil {
		t.Fatal(err)
	}

	if calls != 1 {
		t.Fatalf("expected no in-process retry on poison, got %d calls", calls)
	}
	if len(fake.published) != 1 || fake.published[0].topic != "events.dlq" {
		t.Fatalf("expected single DLQ publish, got %+v", fake.published)
	}
}

func TestTransientThenSuccessRecoversInProcess(t *testing.T) {
	calls := 0
	flaky := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		calls++
		if calls < 3 {
			return fmt.Errorf("%w: blip", kafkaclient.ErrTransient)
		}
		return nil
	}
	policy := DefaultRetryPolicy()
	policy.MaxInProcessAttempts = 3
	handler, fake := wireHandler(policy, flaky)

	if err := handler.Handle(context.Background(), fakeMessage()); err != nil {
		t.Fatal(err)
	}

	if calls != 3 {
		t.Fatalf("expected 3 calls, got %d", calls)
	}
	if len(fake.published) != 0 {
		t.Fatalf("expected recovery before any publish, got %+v", fake.published)
	}
}

func TestTransientExhaustsInProcessThenPublishesRetry(t *testing.T) {
	alwaysFail := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		return fmt.Errorf("%w: still blipping", kafkaclient.ErrTransient)
	}
	policy := DefaultRetryPolicy()
	policy.MaxInProcessAttempts = 2
	policy.MaxRetryTopicAttempts = 5
	policy.JitterRatio = 0
	handler, fake := wireHandler(policy, alwaysFail)

	if err := handler.Handle(context.Background(), fakeMessage()); err != nil {
		t.Fatal(err)
	}

	if len(fake.published) != 1 {
		t.Fatalf("expected 1 publish, got %d", len(fake.published))
	}
	published := fake.published[0]
	if published.topic != "events.retry" {
		t.Fatalf("expected retry topic, got %q", published.topic)
	}
	if retryCount, _ := headers.Get(published.headers, headers.RetryCount); retryCount != "1" {
		t.Fatalf("expected retry count 1, got %q", retryCount)
	}
	if originalTopic, _ := headers.Get(published.headers, headers.OriginalTopic); originalTopic != "events.async" {
		t.Fatalf("expected original topic events.async, got %q", originalTopic)
	}
	if class, _ := headers.Get(published.headers, headers.ErrorClass); class != "TransientError" {
		t.Fatalf("expected error class TransientError, got %q", class)
	}
}

func TestRetryBudgetExhaustedRoutesToDLQ(t *testing.T) {
	alwaysFail := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		return fmt.Errorf("%w: dead", kafkaclient.ErrTransient)
	}
	policy := DefaultRetryPolicy()
	policy.MaxInProcessAttempts = 1
	policy.MaxRetryTopicAttempts = 3
	handler, fake := wireHandler(policy, alwaysFail)

	thirdRetryDelivery := fakeMessage()
	thirdRetryDelivery.Headers = headers.KafkaHeaders{headers.Int(headers.RetryCount, 3)}

	if err := handler.Handle(context.Background(), thirdRetryDelivery); err != nil {
		t.Fatal(err)
	}

	if len(fake.published) != 1 || fake.published[0].topic != "events.dlq" {
		t.Fatalf("expected single DLQ publish, got %+v", fake.published)
	}
}

func TestNonRetryableUnknownErrorGoesToDLQ(t *testing.T) {
	calls := 0
	unknownFailure := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		calls++
		return errors.New("not in retryable list")
	}
	policy := DefaultRetryPolicy()
	policy.Retryable = []error{errors.New("connection error")}
	handler, fake := wireHandler(policy, unknownFailure)

	if err := handler.Handle(context.Background(), fakeMessage()); err != nil {
		t.Fatal(err)
	}

	if calls != 1 {
		t.Fatalf("expected no retry on non-retryable error, got %d calls", calls)
	}
	if len(fake.published) != 1 || fake.published[0].topic != "events.dlq" {
		t.Fatalf("expected single DLQ publish, got %+v", fake.published)
	}
}

func TestDedupeSkipsSeenEvent(t *testing.T) {
	calls := 0
	userHandler := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		calls++
		return nil
	}

	dedupeStore := dedupe.NewInMemoryStore()
	if err := dedupeStore.Mark(context.Background(), "evt-1"); err != nil {
		t.Fatal(err)
	}

	fake := &fakePublisher{}
	handler := NewMessageHandler(userHandler, MessageHandlerConfig{
		Policy:         DefaultRetryPolicy(),
		RetryPublisher: publisher.NewRetryPublisher(fake, "events.retry"),
		DLQPublisher:   publisher.NewDLQPublisher(fake, "events.dlq"),
		DedupeStore:    dedupeStore,
		EventID: func(message kafkaclient.ConsumedMessage) (string, bool) {
			return "evt-1", true
		},
	})

	if err := handler.Handle(context.Background(), fakeMessage()); err != nil {
		t.Fatal(err)
	}

	if calls != 0 {
		t.Fatalf("expected handler to be skipped, got %d calls", calls)
	}
	if len(fake.published) != 0 {
		t.Fatalf("expected no publishes, got %+v", fake.published)
	}
}

func TestCancelledContextPropagatesWithoutRouting(t *testing.T) {
	cancelledContext, cancel := context.WithCancel(context.Background())

	failDuringShutdown := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		cancel()
		return ctx.Err()
	}
	handler, fake := wireHandler(DefaultRetryPolicy(), failDuringShutdown)

	err := handler.Handle(cancelledContext, fakeMessage())

	if !errors.Is(err, context.Canceled) {
		t.Fatalf("expected context.Canceled, got %v", err)
	}
	if len(fake.published) != 0 {
		t.Fatalf("expected no publishes during shutdown, got %+v", fake.published)
	}
}

func TestPublishFailurePropagatesFromHandle(t *testing.T) {
	errBrokerDown := errors.New("broker down")
	poison := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		return kafkaclient.ErrPoison
	}
	fake := &fakePublisher{publishError: errBrokerDown}
	handler := NewMessageHandler(poison, MessageHandlerConfig{
		Policy:         DefaultRetryPolicy(),
		RetryPublisher: publisher.NewRetryPublisher(fake, "events.retry"),
		DLQPublisher:   publisher.NewDLQPublisher(fake, "events.dlq"),
	})

	if err := handler.Handle(context.Background(), fakeMessage()); !errors.Is(err, errBrokerDown) {
		t.Fatalf("expected broker error to propagate, got %v", err)
	}
}

func TestDedupeStoreErrorPropagatesFromHandle(t *testing.T) {
	errStoreDown := errors.New("store down")
	calls := 0
	userHandler := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		calls++
		return nil
	}

	fake := &fakePublisher{}
	handler := NewMessageHandler(userHandler, MessageHandlerConfig{
		Policy:         DefaultRetryPolicy(),
		RetryPublisher: publisher.NewRetryPublisher(fake, "events.retry"),
		DLQPublisher:   publisher.NewDLQPublisher(fake, "events.dlq"),
		DedupeStore:    failingDedupeStore{err: errStoreDown},
		EventID: func(message kafkaclient.ConsumedMessage) (string, bool) {
			return "evt-1", true
		},
	})

	err := handler.Handle(context.Background(), fakeMessage())

	if !errors.Is(err, errStoreDown) {
		t.Fatalf("expected store error to propagate, got %v", err)
	}
	if calls != 0 {
		t.Fatalf("expected handler to be skipped on store error, got %d calls", calls)
	}
}

type failingDedupeStore struct {
	err error
}

func (s failingDedupeStore) Seen(ctx context.Context, eventID string) (bool, error) {
	return false, s.err
}

func (s failingDedupeStore) Mark(
	ctx context.Context,
	eventID string,
	options ...dedupe.MarkOption,
) error {
	return s.err
}

func TestSleepErrorAbortsInProcessRetries(t *testing.T) {
	errSleepInterrupted := errors.New("sleep interrupted")
	calls := 0
	alwaysFail := func(ctx context.Context, message kafkaclient.ConsumedMessage) error {
		calls++
		return fmt.Errorf("%w: blip", kafkaclient.ErrTransient)
	}

	policy := DefaultRetryPolicy()
	policy.MaxInProcessAttempts = 3
	handler, fake := wireHandler(policy, alwaysFail)
	handler.sleep = func(ctx context.Context, duration time.Duration) error {
		return errSleepInterrupted
	}

	err := handler.Handle(context.Background(), fakeMessage())

	if !errors.Is(err, errSleepInterrupted) {
		t.Fatalf("expected sleep error to propagate, got %v", err)
	}
	if calls != 1 {
		t.Fatalf("expected retries to stop after sleep error, got %d calls", calls)
	}
	if len(fake.published) != 0 {
		t.Fatalf("expected no publishes, got %+v", fake.published)
	}
}

func TestInProcessBackoffGrowsLinearlyAndCapsAtCeiling(t *testing.T) {
	expectations := map[int]time.Duration{
		1:  100 * time.Millisecond,
		2:  200 * time.Millisecond,
		10: time.Second,
		50: time.Second,
	}
	for attemptNumber, expected := range expectations {
		if got := inProcessBackoffForAttempt(attemptNumber); got != expected {
			t.Fatalf("attempt %d: expected %v, got %v", attemptNumber, expected, got)
		}
	}
}

func TestSleepUnlessCancelledReturnsImmediatelyForZeroDuration(t *testing.T) {
	if err := sleepUnlessCancelled(context.Background(), 0); err != nil {
		t.Fatal(err)
	}
}

func TestSleepUnlessCancelledCompletesShortSleep(t *testing.T) {
	if err := sleepUnlessCancelled(context.Background(), time.Millisecond); err != nil {
		t.Fatal(err)
	}
}

func TestSleepUnlessCancelledAbortsOnCancelledContext(t *testing.T) {
	cancelledContext, cancel := context.WithCancel(context.Background())
	cancel()

	err := sleepUnlessCancelled(cancelledContext, time.Minute)

	if !errors.Is(err, context.Canceled) {
		t.Fatalf("expected context.Canceled, got %v", err)
	}
}
