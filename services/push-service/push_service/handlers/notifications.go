package handlers

import (
	"services/push-service/internal/log"
	"services/push-service/internal/utilities"
	"services/push-service/push_service/services"
)

type SSENotificationsHandler struct {
	poolService       *services.ClientsPoolService
	projectionService *services.EventsProjectionService
}

func NewSSENotificationsHandler() *SSENotificationsHandler {
	handler := &SSENotificationsHandler{
		poolService:       services.NewClientsPoolService(),
		projectionService: services.NewEventsProjectionService(),
	}
	handler.startBackgroundServices()

	return handler
}

func (snh *SSENotificationsHandler) startBackgroundServices() {
	kafkaChannel := make(chan []byte)

	go snh.projectionService.RunKafkaReceiver(kafkaChannel)
	go snh.poolService.FanoutEvents(snh.projectionService.Events())
}

func (snh *SSENotificationsHandler) Subscribe() (<-chan struct{}, func(), bool) {
	client, registered := snh.poolService.Register()
	if !registered {
		return nil, func() {}, false
	}

	return client.Events(), func() { snh.poolService.Unregister(client) }, true
}

func (snh *SSENotificationsHandler) SpinUntilDone(
	goneChannel <-chan struct{},
	eventsChannel <-chan struct{},
	responseChannel chan<- []byte,
) {
	heartbeatService := services.NewHeartbeatService(HEARTBEAT_INTERVAL)
	go heartbeatService.SpawnHeartbeatMessages(responseChannel)
	defer heartbeatService.StopTicker()

	for {
		select {
		case <-goneChannel:
			return
		case receivedEvent, isOpen := <-eventsChannel:
			if !isOpen {
				return
			}

			buffer, encodeErr := utilities.EncodeStructToBytes(receivedEvent)
			if encodeErr != nil {
				log.PrintError("Failed to encode the Kafka event to byte level", encodeErr)
				continue
			}

			responseChannel <- buffer
		}
	}
}
