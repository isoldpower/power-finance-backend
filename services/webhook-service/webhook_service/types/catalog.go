package types

// WebhookEventType is one row of the subscribable event catalog.
type WebhookEventType struct {
	Event       string   `json:"event"`
	Subject     string   `json:"subject"`
	Description string   `json:"description"`
	OutboxTypes []string `json:"outbox_types"`
}

// EventCatalog mirrors libraries/webhook-catalog-py/webhook_catalog_py/catalog.json.
var EventCatalog = []WebhookEventType{
	{
		Event:       "transaction.created",
		Subject:     "transaction",
		Description: "A transaction was recorded.",
		OutboxTypes: []string{"TransactionCreated"},
	},
	{
		Event:       "transaction.updated",
		Subject:     "transaction",
		Description: "An existing transaction changed.",
		OutboxTypes: []string{"TransactionUpdated", "TransactionMetadataUpdated"},
	},
	{
		Event:       "transaction.deleted",
		Subject:     "transaction",
		Description: "A transaction was cancelled.",
		OutboxTypes: []string{"TransactionDeleted"},
	},
	{
		Event:       "wallet.created",
		Subject:     "wallet",
		Description: "A wallet was opened.",
		OutboxTypes: []string{"WalletCreated"},
	},
	{
		Event:       "wallet.updated",
		Subject:     "wallet",
		Description: "A wallet's details or balance changed.",
		OutboxTypes: []string{"WalletUpdated"},
	},
}

var eventByOutboxType = buildEventByOutboxType()

func buildEventByOutboxType() map[string]string {
	mapping := make(map[string]string, len(EventCatalog))
	for _, entry := range EventCatalog {
		for _, outboxType := range entry.OutboxTypes {
			mapping[outboxType] = entry.Event
		}
	}

	return mapping
}

// IsKnownEvent reports whether a subscription may name this event type.
func IsKnownEvent(event string) bool {
	for _, entry := range EventCatalog {
		if entry.Event == event {
			return true
		}
	}

	return false
}
