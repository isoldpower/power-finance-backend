package services

type webhookEndpointCreatedPayload struct {
	WebhookID string `json:"webhook_id"`
	UserID    int    `json:"user_id"`
	Title     string `json:"title"`
	URL       string `json:"url"`
	Secret    string `json:"secret"`
}

type webhookEndpointUpdatedPayload struct {
	WebhookID string `json:"webhook_id"`
	UserID    int    `json:"user_id"`
	Title     string `json:"title"`
	URL       string `json:"url"`
}

type webhookEndpointDeletedPayload struct {
	WebhookID string `json:"webhook_id"`
	UserID    int    `json:"user_id"`
}

type webhookSecretRotatedPayload struct {
	WebhookID string `json:"webhook_id"`
	UserID    int    `json:"user_id"`
	Secret    string `json:"secret"`
}

type webhookSubscriptionAddedPayload struct {
	SubscriptionID string `json:"subscription_id"`
	WebhookID      string `json:"webhook_id"`
	UserID         int    `json:"user_id"`
	EventType      string `json:"event_type"`
}

type webhookSubscriptionRemovedPayload struct {
	SubscriptionID string `json:"subscription_id"`
	WebhookID      string `json:"webhook_id"`
	UserID         int    `json:"user_id"`
}

type domainEventPayload struct {
	UserID int `json:"user_id"`
}
