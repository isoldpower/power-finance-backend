package kafkaclient

import (
	"errors"
	"fmt"
	"testing"
)

func TestRetryExhaustedMatchesKafkaHandlerError(t *testing.T) {
	if !errors.Is(ErrRetryExhausted, ErrKafkaHandler) {
		t.Fatal("ErrRetryExhausted must match ErrKafkaHandler")
	}
}

func TestErrorClassMapsSentinels(t *testing.T) {
	expectations := map[error]string{
		ErrPoison:                                "PoisonError",
		ErrTransient:                             "TransientError",
		ErrRetryExhausted:                        "RetryExhaustedError",
		ErrKafkaHandler:                          "KafkaHandlerError",
		fmt.Errorf("%w: bad payload", ErrPoison): "PoisonError",
		fmt.Errorf("%w: blip", ErrTransient):     "TransientError",
	}
	for err, expectedClass := range expectations {
		if got := ErrorClass(err); got != expectedClass {
			t.Fatalf("expected %q for %v, got %q", expectedClass, err, got)
		}
	}
}

func TestErrorClassUsesGoTypeNameForCustomErrors(t *testing.T) {
	if class := ErrorClass(&customTestError{}); class != "kafkaclient.customTestError" {
		t.Fatalf("expected kafkaclient.customTestError, got %q", class)
	}
}

type customTestError struct{}

func (e *customTestError) Error() string { return "custom" }
