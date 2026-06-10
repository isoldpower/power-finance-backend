package services

import (
	"services/push-service/internal/log"
)

type EventsProjectionService struct {
	eventsChannel chan struct{}
}

func NewEventsProjectionService() *EventsProjectionService {
	return &EventsProjectionService{
		eventsChannel: make(chan struct{}),
	}
}

func (eps *EventsProjectionService) Events() <-chan struct{} {
	return eps.eventsChannel
}

func (eps *EventsProjectionService) RunKafkaReceiver(kafkaChannel <-chan []byte) {
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

func (eps *EventsProjectionService) translateKafkaMessage(kafkaMessage []byte) ([]struct{}, error) {
	return make([]struct{}, 0), nil
}
