package publisher

import (
	"context"
	"time"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/headers"
)

const DefaultDLQTopic = "events.dlq"

type DLQPublisher struct {
	publisher MessagePublisher
	topic     string
}

func NewDLQPublisher(publisher MessagePublisher, topic string) *DLQPublisher {
	if topic == "" {
		topic = DefaultDLQTopic
	}

	return &DLQPublisher{publisher: publisher, topic: topic}
}

type DLQPublication struct {
	Error         error
	TotalAttempts int
	FirstFailedAt time.Time
	CorrelationID string
}

func (p *DLQPublisher) Publish(
	ctx context.Context,
	message kafkaclient.ConsumedMessage,
	publication DLQPublication,
) error {
	originalTopic := resolveOriginalTopic(message)
	firstFailedAt := resolveFirstFailedAt(message, publication.FirstFailedAt)
	correlationID := resolveCorrelationID(message, publication.CorrelationID)

	dlqHeaders := headers.Merge(
		message.Headers,
		headers.String(headers.OriginalTopic, originalTopic),
		headers.Int(headers.OriginalPartition, int64(message.Partition)),
		headers.Int(headers.OriginalOffset, message.Offset),
		headers.Int(headers.RetryCount, int64(publication.TotalAttempts)),
		headers.Time(headers.FirstFailedAt, firstFailedAt),
		headers.Time(headers.FailedAt, time.Now().UTC()),
		headers.String(headers.ErrorClass, kafkaclient.ErrorClass(publication.Error)),
		headers.String(headers.ErrorMessage, truncate(publication.Error.Error(), errorMessageMaxBytes)),
		headers.String(headers.ErrorStack, truncate(errorDetails(publication.Error), errorStackMaxBytes)),
	)

	if correlationID != "" {
		dlqHeaders = headers.Merge(
			dlqHeaders,
			headers.String(headers.CorrelationID, correlationID),
		)
	}

	return p.publisher.Publish(
		ctx,
		p.topic,
		message.Key,
		valueOrEmpty(message),
		dlqHeaders,
	)
}
