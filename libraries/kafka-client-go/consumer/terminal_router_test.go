package consumer

import (
	"context"
	"errors"
	"testing"

	"github.com/power-finance/kafka-client-go/headers"
	"github.com/power-finance/kafka-client-go/publisher"
)

func TestImmediateFailureAlwaysGoesToDLQ(t *testing.T) {
	policy := DefaultRetryPolicy()
	policy.MaxRetryTopicAttempts = 10
	router, fake := wireRouter(policy)
	retryContext := RetryContext{RetryTopicAttemptsConsumed: 2}

	err := router.RouteImmediateFailure(
		context.Background(),
		fakeMessage(),
		errors.New("nope"),
		retryContext,
		1,
		"non_retryable",
	)

	if err != nil {
		t.Fatal(err)
	}
	if len(fake.published) != 1 || fake.published[0].topic != "events.dlq" {
		t.Fatalf("expected single DLQ publish, got %+v", fake.published)
	}
}

func TestImmediateFailureReportsTotalAttemptsAsSum(t *testing.T) {
	router, fake := wireRouter(DefaultRetryPolicy())
	retryContext := RetryContext{RetryTopicAttemptsConsumed: 4}

	err := router.RouteImmediateFailure(
		context.Background(),
		fakeMessage(),
		errors.New("boom"),
		retryContext,
		3,
		"poison",
	)

	if err != nil {
		t.Fatal(err)
	}
	if totalAttempts := headers.GetInt(fake.published[0].headers, headers.RetryCount, 0); totalAttempts != 7 {
		t.Fatalf("expected total attempts 4+3=7, got %d", totalAttempts)
	}
}

func TestTerminalFailureWithBudgetRemainingGoesToRetryTopic(t *testing.T) {
	policy := DefaultRetryPolicy()
	policy.MaxRetryTopicAttempts = 5
	policy.JitterRatio = 0
	router, fake := wireRouter(policy)
	retryContext := RetryContext{RetryTopicAttemptsConsumed: 2}

	err := router.RouteTerminalFailure(
		context.Background(),
		fakeMessage(),
		errors.New("blip"),
		retryContext,
		3,
	)

	if err != nil {
		t.Fatal(err)
	}
	if len(fake.published) != 1 || fake.published[0].topic != "events.retry" {
		t.Fatalf("expected single retry-topic publish, got %+v", fake.published)
	}
}

func TestRetryTopicAttemptNumberIsIncrementedByOne(t *testing.T) {
	policy := DefaultRetryPolicy()
	policy.MaxRetryTopicAttempts = 5
	policy.JitterRatio = 0
	router, fake := wireRouter(policy)
	retryContext := RetryContext{RetryTopicAttemptsConsumed: 2}

	err := router.RouteTerminalFailure(
		context.Background(),
		fakeMessage(),
		errors.New("blip"),
		retryContext,
		3,
	)

	if err != nil {
		t.Fatal(err)
	}
	if nextAttempt := headers.GetInt(fake.published[0].headers, headers.RetryCount, 0); nextAttempt != 3 {
		t.Fatalf("expected next attempt 3, got %d", nextAttempt)
	}
	if _, found := headers.GetTime(fake.published[0].headers, headers.RetryAt); !found {
		t.Fatal("expected x-retry-at header to be stamped")
	}
}

func TestTerminalFailureWithBudgetExhaustedGoesToDLQ(t *testing.T) {
	policy := DefaultRetryPolicy()
	policy.MaxRetryTopicAttempts = 5
	router, fake := wireRouter(policy)
	retryContext := RetryContext{RetryTopicAttemptsConsumed: 5}

	err := router.RouteTerminalFailure(
		context.Background(),
		fakeMessage(),
		errors.New("dead"),
		retryContext,
		3,
	)

	if err != nil {
		t.Fatal(err)
	}
	published := fake.published[0]
	if published.topic != "events.dlq" {
		t.Fatalf("expected DLQ publish, got %q", published.topic)
	}
	if totalAttempts := headers.GetInt(published.headers, headers.RetryCount, 0); totalAttempts != 8 {
		t.Fatalf("expected total attempts 5+3=8, got %d", totalAttempts)
	}
}

func TestRetryPublishFailurePropagatesFromRouter(t *testing.T) {
	errBrokerDown := errors.New("broker down")
	fake := &fakePublisher{publishError: errBrokerDown}
	router := NewTerminalRouter(
		DefaultRetryPolicy(),
		publisher.NewRetryPublisher(fake, "events.retry"),
		publisher.NewDLQPublisher(fake, "events.dlq"),
		nil,
	)

	err := router.RouteTerminalFailure(
		context.Background(),
		fakeMessage(),
		errors.New("blip"),
		RetryContext{RetryTopicAttemptsConsumed: 0},
		1,
	)

	if !errors.Is(err, errBrokerDown) {
		t.Fatalf("expected broker error from retry publish, got %v", err)
	}
}

func TestExhaustedDLQPublishFailurePropagatesFromRouter(t *testing.T) {
	errBrokerDown := errors.New("broker down")
	fake := &fakePublisher{publishError: errBrokerDown}
	policy := DefaultRetryPolicy()
	policy.MaxRetryTopicAttempts = 1
	router := NewTerminalRouter(
		policy,
		publisher.NewRetryPublisher(fake, "events.retry"),
		publisher.NewDLQPublisher(fake, "events.dlq"),
		nil,
	)

	err := router.RouteTerminalFailure(
		context.Background(),
		fakeMessage(),
		errors.New("dead"),
		RetryContext{RetryTopicAttemptsConsumed: 1},
		1,
	)

	if !errors.Is(err, errBrokerDown) {
		t.Fatalf("expected broker error from DLQ publish, got %v", err)
	}
}
