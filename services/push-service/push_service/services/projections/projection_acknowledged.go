package projections

import (
	"encoding/json"
	"fmt"

	"services/push-service/push_service/types"
)

// acknowledgedResource is deliberately thin: the id and the new timestamp are
// the only things that changed.
type acknowledgedResource struct {
	ID             string `json:"id"`
	AcknowledgedAt string `json:"acknowledged_at"`
}

// notificationsAcknowledgedPayload is the transfer protocol object
// representing projected Kafka event.
type notificationsAcknowledgedPayload struct {
	NotificationIDs []string `json:"notification_ids"`
	AcknowledgedAt  string   `json:"acknowledged_at"`
}

// projectNotificationsAcknowledged fans one batch out into one event per id: a
// client tracks notifications individually and has no use for the batch a
// second device happened to acknowledge them in.
func projectNotificationsAcknowledged(message types.OutboxEvent) ([]types.OutboxEvent, error) {
	var payload notificationsAcknowledgedPayload
	if unmarshalErr := json.Unmarshal(message.Payload, &payload); unmarshalErr != nil {
		return nil, fmt.Errorf("decoding NotificationsAcknowledged: %w", unmarshalErr)
	}

	projected := make([]types.OutboxEvent, 0, len(payload.NotificationIDs))
	for _, notificationID := range payload.NotificationIDs {
		encoded, marshalErr := json.Marshal(acknowledgedResource{
			ID:             notificationID,
			AcknowledgedAt: payload.AcknowledgedAt,
		})
		if marshalErr != nil {
			return nil, fmt.Errorf("encoding notification.acknowledged: %w", marshalErr)
		}

		projected = append(projected, types.OutboxEvent{
			EventID:       notificationID,
			EventType:     NotificationAcknowledgedEvent,
			AggregateType: message.AggregateType,
			UserID:        message.UserID,
			Payload:       encoded,
		})
	}

	return projected, nil
}
