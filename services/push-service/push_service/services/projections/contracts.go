package projections

const (
	NotificationCreatedEvent      = "notification.created"
	NotificationAcknowledgedEvent = "notification.acknowledged"
)
const (
	notificationCreatedMessage       = "NotificationCreated"
	notificationsAcknowledgedMessage = "NotificationsAcknowledged"
)

// severityNames maps the proto enum onto the API vocabulary.
var severityNames = map[string]string{
	"NOTIFICATION_SEVERITY_INFO":     "info",
	"NOTIFICATION_SEVERITY_WARNING":  "warning",
	"NOTIFICATION_SEVERITY_CRITICAL": "critical",
}

// defaultSeverity is used when proto message enum is absent.
const defaultSeverity = "info"

// subject represents the notification subject over which the notification is called.
type subject struct {
	Type string `json:"type"`
	ID   string `json:"id"`
}
