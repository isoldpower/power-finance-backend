package publisher

import (
	"context"
	"time"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/headers"
)

const DefaultRetryTopic = "events.retry"

type RetryPublisher struct {
	publisher MessagePublisher
	topic     string
}

func NewRetryPublisher(publisher MessagePublisher, topic string) *RetryPublisher {
	if topic == "" {
		topic = DefaultRetryTopic
	}

	return &RetryPublisher{publisher: publisher, topic: topic}
}

type RetryPublication struct {
	Error         error
	NextRetryAt   time.Time
	Attempt       int
	FirstFailedAt time.Time
	CorrelationID string
}

func (rp *RetryPublisher) Publish(
	ctx context.Context,
	message kafkaclient.ConsumedMessage,
	publication RetryPublication,
) error {
	originalTopic := resolveOriginalTopic(message)
	firstFailedAt := resolveFirstFailedAt(message, publication.FirstFailedAt)
	correlationID := resolveCorrelationID(message, publication.CorrelationID)

	republishHeaders := headers.Merge(
		message.Headers,
		headers.String(headers.OriginalTopic, originalTopic),
		headers.Int(headers.OriginalPartition, int64(message.Partition)),
		headers.Int(headers.OriginalOffset, message.Offset),
		headers.Int(headers.RetryCount, int64(publication.Attempt)),
		headers.Time(headers.RetryAt, publication.NextRetryAt),
		headers.Time(headers.FirstFailedAt, firstFailedAt),
		headers.Time(headers.FailedAt, time.Now().UTC()),
		headers.String(headers.ErrorClass, kafkaclient.ErrorClass(publication.Error)),
		headers.String(headers.ErrorMessage, truncate(publication.Error.Error(), errorMessageMaxBytes)),
		headers.String(headers.ErrorStack, truncate(errorDetails(publication.Error), errorStackMaxBytes)),
	)
	if correlationID != "" {
		republishHeaders = headers.Merge(
			republishHeaders,
			headers.String(headers.CorrelationID, correlationID),
		)
	}

	return rp.publisher.Publish(
		ctx,
		rp.topic,
		message.Key,
		valueOrEmpty(message),
		republishHeaders,
	)
}

func resolveOriginalTopic(message kafkaclient.ConsumedMessage) string {
	existingOriginalTopic, _ := headers.Get(message.Headers, headers.OriginalTopic)
	if existingOriginalTopic != "" {
		return existingOriginalTopic
	}

	return message.Topic
}

func resolveFirstFailedAt(
	message kafkaclient.ConsumedMessage,
	explicitFirstFailedAt time.Time,
) time.Time {
	if !explicitFirstFailedAt.IsZero() {
		return explicitFirstFailedAt
	}
	if firstFailedAtFromHeaders, found := headers.GetTime(message.Headers, headers.FirstFailedAt); found {
		return firstFailedAtFromHeaders
	}

	return time.Now().UTC()
}

func resolveCorrelationID(
	message kafkaclient.ConsumedMessage,
	explicitCorrelationID string,
) string {
	if explicitCorrelationID != "" {
		return explicitCorrelationID
	}
	correlationIDFromHeaders, _ := headers.Get(message.Headers, headers.CorrelationID)

	return correlationIDFromHeaders
}

func valueOrEmpty(message kafkaclient.ConsumedMessage) []byte {
	if message.Value == nil {
		return []byte{}
	}

	return message.Value
}
