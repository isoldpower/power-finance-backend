package services

import (
	"errors"
	"log/slog"

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

func (eps *EventsProjectionService) Events() <-chan types.OutboxEvent {
	return eps.eventsChannel
}

func (eps *EventsProjectionService) RunKafkaReceiver(kafkaChannel <-chan types.OutboxEvent) {
	defer close(eps.eventsChannel)

	for kafkaMessage := range kafkaChannel {
		projectedEvents, translateErr := eps.translateKafkaMessage(kafkaMessage)
		if translateErr != nil {
			slog.Warn(
				"dropping malformed kafka message",
				"event_id", kafkaMessage.EventID,
				"error", translateErr,
			)
			continue
		}

		for _, projectedEvent := range projectedEvents {
			slog.Debug(
				"kafka message projected",
				"event_id", projectedEvent.EventID,
				"event_type", projectedEvent.EventType,
			)
			eps.eventsChannel <- projectedEvent
		}
	}
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

	return []types.OutboxEvent{kafkaMessage}, nil
}
