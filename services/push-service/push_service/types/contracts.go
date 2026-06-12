package types

// ClientSubscription is a single client's event feed; Cancel detaches it from the pool.
type ClientSubscription interface {
	Events() <-chan OutboxEvent
	Cancel()
}

// ClientsPool fans events out to per-user subscriptions.
type ClientsPool interface {
	FanoutEvents(eventsChannel <-chan OutboxEvent)
	Subscribe(externalUserID string) (ClientSubscription, bool)
}

// EventsProjector translates raw Kafka events into client-facing events.
type EventsProjector interface {
	RunKafkaReceiver(kafkaChannel <-chan OutboxEvent)
	Events() <-chan OutboxEvent
}

// Heartbeat emits SSE keepalive frames until stopped.
type Heartbeat interface {
	SpawnHeartbeatMessages(receiver chan<- []byte)
	StopTicker()
}

// HeartbeatFactory builds one Heartbeat per SSE connection.
type HeartbeatFactory func() Heartbeat

// NotificationsStream is the presentation-facing surface of the SSE pipeline.
type NotificationsStream interface {
	Subscribe(externalUserID string) (<-chan OutboxEvent, func(), bool)
	SpinUntilDone(goneChannel <-chan struct{}, eventsChannel <-chan OutboxEvent, responseChannel chan<- []byte)
}
