package services

import (
	"errors"

	"services/push-service/internal/log"
)

type EventsProjectionService struct {
	eventsChannel chan OutboxEvent
}

func NewEventsProjectionService() *EventsProjectionService {
	return &EventsProjectionService{
		eventsChannel: make(chan OutboxEvent),
	}
}

func (eps *EventsProjectionService) Events() <-chan OutboxEvent {
	return eps.eventsChannel
}

func (eps *EventsProjectionService) RunKafkaReceiver(kafkaChannel <-chan OutboxEvent) {
	defer close(eps.eventsChannel)

	for kafkaMessage := range kafkaChannel {
		projectedEvents, translateErr := eps.translateKafkaMessage(kafkaMessage)
		if translateErr != nil {
			log.PrintError("Error translating Kafka message", translateErr)
			continue
		}

		log.Infoln("Received new valid Kafka message")
		for _, projectedEvent := range projectedEvents {
			eps.eventsChannel <- projectedEvent
		}
	}
}

func (eps *EventsProjectionService) translateKafkaMessage(
	kafkaMessage OutboxEvent,
) ([]OutboxEvent, error) {
	if kafkaMessage.EventType == "" {
		return nil, errors.New("outbox event is missing the event_type header")
	}
	if len(kafkaMessage.Payload) == 0 {
		return nil, errors.New("outbox event carries an empty payload")
	}

	return []OutboxEvent{kafkaMessage}, nil
}
