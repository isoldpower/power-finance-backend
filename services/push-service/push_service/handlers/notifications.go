package handlers

import (
	"services/push-service/push_service/services"
)

type SSENotificationsHandler struct {
	poolService       *services.ClientsPoolService
	projectionService *services.EventsProjectionService
	kafkaChannel      chan services.OutboxEvent
}

func NewSSENotificationsHandler() *SSENotificationsHandler {
	handler := &SSENotificationsHandler{
		poolService:       services.NewClientsPoolService(),
		projectionService: services.NewEventsProjectionService(),
		kafkaChannel:      make(chan services.OutboxEvent),
	}
	handler.startBackgroundServices()

	return handler
}

func (snh *SSENotificationsHandler) startBackgroundServices() {
	go snh.projectionService.RunKafkaReceiver(snh.kafkaChannel)
	go snh.poolService.FanoutEvents(snh.projectionService.Events())
}

func (snh *SSENotificationsHandler) KafkaSink() chan<- services.OutboxEvent {
	return snh.kafkaChannel
}

func (snh *SSENotificationsHandler) Subscribe(
	externalUserID string,
) (<-chan services.OutboxEvent, func(), bool) {
	client, registered := snh.poolService.Register(externalUserID)
	if !registered {
		return nil, func() {}, false
	}

	return client.Events(), func() { snh.poolService.Unregister(client) }, true
}

func (snh *SSENotificationsHandler) SpinUntilDone(
	goneChannel <-chan struct{},
	eventsChannel <-chan services.OutboxEvent,
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

			responseChannel <- formatServerSentEvent(receivedEvent)
		}
	}
}
