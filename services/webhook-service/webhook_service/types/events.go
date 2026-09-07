package types

// OutboxEvent is a decoded outbox row as the services layer dispatches on it.
type OutboxEvent struct {
	EventID        string
	EventType      string
	AggregateType  string
	UserExternalID string
	Payload        []byte
}

// WebhookEventTypeFor maps an outbox event type to its subscription type, or blank when undeliverable.
func WebhookEventTypeFor(outboxEventType string) string {
	return eventByOutboxType[outboxEventType]
}
