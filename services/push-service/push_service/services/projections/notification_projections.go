package projections

import (
	"services/push-service/push_service/types"
)

// ProjectNotificationEvents turns one outbox message into the events the stream
// documents, or none at all.
func ProjectNotificationEvents(message types.OutboxEvent) ([]types.OutboxEvent, error) {
	switch message.EventType {
	case notificationCreatedMessage:
		return projectNotificationCreated(message)
	case notificationsAcknowledgedMessage:
		return projectNotificationsAcknowledged(message)
	default:
		return nil, nil
	}
}
