package consumer

import (
	"time"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/headers"
)

type RetryContext struct {
	RetryTopicAttemptsConsumed int
	FirstFailedAt              time.Time
}

func RetryContextFromMessage(message kafkaclient.ConsumedMessage) RetryContext {
	firstFailedAt, _ := headers.GetTime(message.Headers, headers.FirstFailedAt)

	return RetryContext{
		RetryTopicAttemptsConsumed: headers.GetInt(message.Headers, headers.RetryCount, 0),
		FirstFailedAt:              firstFailedAt,
	}
}

func (c RetryContext) FirstFailedAtOrNow() time.Time {
	if c.FirstFailedAt.IsZero() {
		return time.Now().UTC()
	}

	return c.FirstFailedAt
}
