package services

import (
	"context"
	"errors"
	"log/slog"
	"services/push-service/push_service/services/projections"

	"services/push-service/internal/metrics"
	"services/push-service/push_service/types"
)

type EventsProjectionService struct {
	eventsChannel chan types.OutboxEvent
}

func NewEventsProjectionService() *EventsProjectionService {
	return &EventsProjectionService{
		eventsChannel: make(chan types.OutboxEvent),
	}
}

// Events exposes events fanout channel assigned to the service.
func (eps *EventsProjectionService) Events() <-chan types.OutboxEvent {
	return eps.eventsChannel
}

// RunKafkaReceiver runs a receiver that handles received Kafka messages and
// translates them to related client-oriented notifications. It returns when the
// kafka channel closes or ctx is cancelled, closing the events channel on exit.
func (eps *EventsProjectionService) RunKafkaReceiver(ctx context.Context, kafkaChannel <-chan types.OutboxEvent) {
	defer close(eps.eventsChannel)

	for {
		select {
		case <-ctx.Done():
			return
		case kafkaMessage, isOpen := <-kafkaChannel:
			if !isOpen {
				return
			}
			if !eps.forwardProjectedEvents(ctx, kafkaMessage) {
				return
			}
		}
	}
}

// forwardProjectedEvents projects a message and forwards each result; it returns
// false when ctx is cancelled mid-forward so the caller can stop.
func (eps *EventsProjectionService) forwardProjectedEvents(
	ctx context.Context,
	kafkaMessage types.OutboxEvent,
) bool {
	projectedEvents, translateErr := eps.translateKafkaMessage(kafkaMessage)
	if translateErr != nil {
		metrics.EventDroppedMalformed()
		slog.Warn(
			"dropping malformed kafka message",
			"event_id", kafkaMessage.EventID,
			"error", translateErr,
		)

		return true
	}

	for _, projectedEvent := range projectedEvents {
		slog.Debug(
			"kafka message projected",
			"event_id", projectedEvent.EventID,
			"event_type", projectedEvent.EventType,
		)
		select {
		case <-ctx.Done():
			return false
		case eps.eventsChannel <- projectedEvent:
			metrics.EventProjected()
		}
	}

	return true
}

func (eps *EventsProjectionService) translateKafkaMessage(
	kafkaMessage types.OutboxEvent,
) ([]types.OutboxEvent, error) {
	if kafkaMessage.EventType == "" {
		return nil, errors.New("outbox event is missing the event_type header")
	}
	if len(kafkaMessage.Payload) == 0 {
		return nil, errors.New("outbox event carries an empty payload")
	}

	return projections.ProjectNotificationEvents(kafkaMessage)
}
