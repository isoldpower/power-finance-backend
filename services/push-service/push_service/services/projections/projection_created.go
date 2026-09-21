package projections

import (
	"encoding/json"
	"fmt"

	"services/push-service/push_service/types"
)

// notificationResource is the client-facing shape, identical to one element of
// GET /notifications — so a client prepends it without a follow-up request.
type notificationResource struct {
	ID             string   `json:"id"`
	CreatedAt      string   `json:"created_at"`
	UpdatedAt      *string  `json:"updated_at"`
	DeletedAt      *string  `json:"deleted_at"`
	Severity       string   `json:"severity"`
	Title          string   `json:"title"`
	Body           string   `json:"body"`
	Subject        *subject `json:"subject"`
	AcknowledgedAt *string  `json:"acknowledged_at"`
}

// notificationCreatedPayload is the producer's shape, not the client's.
type notificationCreatedPayload struct {
	NotificationID string `json:"notification_id"`
	Title          string `json:"title"`
	Body           string `json:"body"`
	Severity       string `json:"severity"`
	SubjectType    string `json:"subject_type"`
	SubjectID      string `json:"subject_id"`
	CreatedAt      string `json:"created_at"`
}

func projectNotificationCreated(message types.OutboxEvent) ([]types.OutboxEvent, error) {
	var payload notificationCreatedPayload
	if unmarshalErr := json.Unmarshal(message.Payload, &payload); unmarshalErr != nil {
		return nil, fmt.Errorf("decoding NotificationCreated: %w", unmarshalErr)
	}
	if payload.NotificationID == "" {
		return nil, fmt.Errorf("NotificationCreated carries no notification id")
	}

	resource := notificationResource{
		ID:        payload.NotificationID,
		CreatedAt: payload.CreatedAt,
		Severity:  severityName(payload.Severity),
		Title:     payload.Title,
		Body:      payload.Body,
		Subject:   subjectOf(payload),
	}

	encoded, marshalErr := json.Marshal(resource)
	if marshalErr != nil {
		return nil, fmt.Errorf("encoding notification.created: %w", marshalErr)
	}

	return []types.OutboxEvent{{
		EventID:       payload.NotificationID,
		EventType:     NotificationCreatedEvent,
		AggregateType: message.AggregateType,
		UserID:        message.UserID,
		Payload:       encoded,
	}}, nil
}
