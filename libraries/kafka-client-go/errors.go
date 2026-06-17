package kafkaclient

import (
	"errors"
	"fmt"
	"strings"
)

var (
	ErrKafkaHandler = errors.New("kafka handler error")
	ErrTransient    = errors.New("transient error")
	ErrPoison       = errors.New("poison message")
)

var ErrRetryExhausted = fmt.Errorf("%w: retry exhausted", ErrKafkaHandler)

func ErrorClass(err error) string {
	switch {
	case errors.Is(err, ErrPoison):
		return "PoisonError"
	case errors.Is(err, ErrRetryExhausted):
		return "RetryExhaustedError"
	case errors.Is(err, ErrTransient):
		return "TransientError"
	case errors.Is(err, ErrKafkaHandler):
		return "KafkaHandlerError"
	}

	return strings.TrimPrefix(fmt.Sprintf("%T", err), "*")
}
