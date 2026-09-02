package types

import "time"

type DeliveryStatus string

const (
	DeliveryPending        DeliveryStatus = "pending"
	DeliveryInProgress     DeliveryStatus = "in_progress"
	DeliveryRetryScheduled DeliveryStatus = "retry_scheduled"
	DeliverySuccess        DeliveryStatus = "success"
	DeliveryFailed         DeliveryStatus = "failed"
)

// DeliveryStatuses is the closed vocabulary the delivery log filters on.
var DeliveryStatuses = []DeliveryStatus{
	DeliveryPending,
	DeliveryInProgress,
	DeliveryRetryScheduled,
	DeliverySuccess,
	DeliveryFailed,
}

// IsKnownDeliveryStatus reports whether a `status` filter names a real status.
func IsKnownDeliveryStatus(candidate string) bool {
	for _, status := range DeliveryStatuses {
		if string(status) == candidate {
			return true
		}
	}

	return false
}

type WebhookEndpoint struct {
	ID             string
	UserID         int
	UserExternalID string
	Title          string
	URL            string
	Secret         string
	SecretVersion  int
	IsActive       bool
}

// EndpointSecrets is what an endpoint can currently sign with: the live secret
// and, inside a rotation's grace window, the one it replaced.
type EndpointSecrets struct {
	Secret                  string
	SecretVersion           int
	PreviousSecret          string
	PreviousSecretVersion   int
	PreviousSecretExpiresAt *time.Time
}

// For returns the secret that signs a delivery pinned to secretVersion.
func (s EndpointSecrets) For(secretVersion int, now time.Time) string {
	if secretVersion == s.SecretVersion || s.PreviousSecret == "" {
		return s.Secret
	}
	if secretVersion != s.PreviousSecretVersion {
		return s.Secret
	}
	if s.PreviousSecretExpiresAt == nil || now.After(*s.PreviousSecretExpiresAt) {
		return s.Secret
	}

	return s.PreviousSecret
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
	SecretVersion  int
	NextAttemptAt  *time.Time
	LastError      string
	CreatedAt      time.Time
	UpdatedAt      time.Time
}

// SecretRotation is what a WebhookSecretRotated event installs: the new secret
// and the window the replaced one stays valid for.
type SecretRotation struct {
	WebhookID               string
	Secret                  string
	SecretVersion           int
	PreviousSecret          string
	PreviousSecretVersion   int
	PreviousSecretExpiresAt *time.Time
}
