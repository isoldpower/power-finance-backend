package types

import "time"

type DeliveryStatus string

const (
	DeliveryPending DeliveryStatus = "pending"
	DeliverySuccess DeliveryStatus = "success"
	DeliveryFailed  DeliveryStatus = "failed"
)

type WebhookEndpoint struct {
	ID             string
	UserID         int
	UserExternalID string
	Title          string
	URL            string
	Secret         string
	IsActive       bool
}

type WebhookSubscription struct {
	ID        string
	WebhookID string
	UserID    int
	EventType string
}

type Delivery struct {
	ID             string
	WebhookID      string
	UserID         int
	UserExternalID string
	EventID        string
	EventType      string
	TargetURL      string
	Payload        []byte
	Status         DeliveryStatus
	Attempts       int
	NextAttemptAt  time.Time
	LastError      string
}
