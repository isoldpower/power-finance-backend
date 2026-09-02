package types

type OutboxEvent struct {
	EventID        string
	EventType      string
	AggregateType  string
	UserExternalID string
	Payload        []byte
}

// WebhookEventTypeFor maps a domain outbox event type to the webhook
// subscription type, or blank when the event is not webhook-deliverable.
func WebhookEventTypeFor(outboxEventType string) string {
	return eventByOutboxType[outboxEventType]
}
