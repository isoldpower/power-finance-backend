package kafka

import (
	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/envelope"
	"github.com/power-finance/kafka-client-go/headers"

	"services/webhook-service/webhook_service/types"
)

func headerValue(message kafkaclient.ConsumedMessage, name string) (string, bool) {
	return headers.Get(message.Headers, name)
}

// OutboxEventFromMessage projects a consumed Kafka message into the flat
// outbox event the services layer dispatches on.
func OutboxEventFromMessage(message kafkaclient.ConsumedMessage) types.OutboxEvent {
	eventID, _ := headerValue(message, envelope.EventID)
	eventType, _ := headerValue(message, envelope.EventType)
	aggregateType, _ := headerValue(message, envelope.AggregateType)

	return types.OutboxEvent{
		EventID:        eventID,
		EventType:      eventType,
		AggregateType:  aggregateType,
		UserExternalID: string(message.Key),
		Payload:        message.Value,
	}
}
