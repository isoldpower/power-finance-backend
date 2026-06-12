package handlers

import (
	"services/push-service/push_service/types"
)

type SSENotificationsHandler struct {
	poolService       types.ClientsPool
	projectionService types.EventsProjector
	newHeartbeat      types.HeartbeatFactory
	kafkaChannel      chan types.OutboxEvent
}

func NewSSENotificationsHandler(
	poolService types.ClientsPool,
	projectionService types.EventsProjector,
	newHeartbeat types.HeartbeatFactory,
) *SSENotificationsHandler {
	return &SSENotificationsHandler{
		poolService:       poolService,
		projectionService: projectionService,
		newHeartbeat:      newHeartbeat,
		kafkaChannel:      make(chan types.OutboxEvent),
	}
}

// Start launches the projection and fanout pipelines.
func (snh *SSENotificationsHandler) Start() {
	go snh.projectionService.RunKafkaReceiver(snh.kafkaChannel)
	go snh.poolService.FanoutEvents(snh.projectionService.Events())
}

// KafkaSink returns the Kafka event channel associated with handler.
func (snh *SSENotificationsHandler) KafkaSink() chan<- types.OutboxEvent {
	return snh.kafkaChannel
}

// Subscribe allows to subscribe to user-based events fanout.
func (snh *SSENotificationsHandler) Subscribe(
	externalUserID string,
) (<-chan types.OutboxEvent, func(), bool) {
	subscription, registered := snh.poolService.Subscribe(externalUserID)
	if !registered {
		return nil, func() {}, false
	}

	return subscription.Events(), subscription.Cancel, true
}

// SpinUntilDone runs a loop which handles events and fans them out to related channel
// until the connection is gone (client disconnected).
func (snh *SSENotificationsHandler) SpinUntilDone(
	goneChannel <-chan struct{},
	eventsChannel <-chan types.OutboxEvent,
	responseChannel chan<- []byte,
) {
	heartbeatService := snh.newHeartbeat()
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
