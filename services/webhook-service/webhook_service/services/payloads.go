package services

import "time"

type webhookEndpointCreatedPayload struct {
	WebhookID     string `json:"webhook_id"`
	UserID        int    `json:"user_id"`
	Title         string `json:"title"`
	URL           string `json:"url"`
	Secret        string `json:"secret"`
	SecretVersion int    `json:"secret_version"`
	Enabled       bool   `json:"enabled"`
}

type webhookEndpointUpdatedPayload struct {
	WebhookID string `json:"webhook_id"`
	UserID    int    `json:"user_id"`
	Title     string `json:"title"`
	URL       string `json:"url"`
	Enabled   bool   `json:"enabled"`
}

type webhookEndpointDeletedPayload struct {
	WebhookID string `json:"webhook_id"`
	UserID    int    `json:"user_id"`
}

type webhookSecretRotatedPayload struct {
	WebhookID               string     `json:"webhook_id"`
	UserID                  int        `json:"user_id"`
	Secret                  string     `json:"secret"`
	SecretVersion           int        `json:"secret_version"`
	PreviousSecret          string     `json:"previous_secret"`
	PreviousSecretVersion   int        `json:"previous_secret_version"`
	PreviousSecretExpiresAt *time.Time `json:"previous_secret_expires_at"`
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
