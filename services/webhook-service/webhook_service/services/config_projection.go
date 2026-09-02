package services

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"time"

	"services/webhook-service/webhook_service/types"
)

type configStore interface {
	UpsertEndpoint(ctx context.Context, endpoint types.WebhookEndpoint, at time.Time) error
	UpdateEndpoint(ctx context.Context, webhookID, title, url string, enabled bool, at time.Time) error
	RotateSecret(ctx context.Context, rotation types.SecretRotation, at time.Time) error
	DeleteEndpoint(ctx context.Context, webhookID string) error
	AddSubscription(ctx context.Context, subscription types.WebhookSubscription, at time.Time) error
	RemoveSubscription(ctx context.Context, subscriptionID string) error
}

type ConfigProjection struct {
	store configStore
}

func NewConfigProjection(store configStore) *ConfigProjection {
	return &ConfigProjection{store: store}
}

// Handles reports whether the projection owns the given outbox event type.
func (p *ConfigProjection) Handles(eventType string) bool {
	switch eventType {
	case "WebhookEndpointCreated",
		"WebhookEndpointUpdated",
		"WebhookEndpointDeleted",
		"WebhookSecretRotated",
		"WebhookSubscriptionAdded",
		"WebhookSubscriptionRemoved":
		return true
	default:
		return false
	}
}

func (p *ConfigProjection) Apply(ctx context.Context, event types.OutboxEvent) error {
	now := time.Now().UTC()

	switch event.EventType {
	case "WebhookEndpointCreated":
		return p.applyEndpointCreated(ctx, event, now)
	case "WebhookEndpointUpdated":
		return p.applyEndpointUpdated(ctx, event, now)
	case "WebhookEndpointDeleted":
		return p.applyEndpointDeleted(ctx, event)
	case "WebhookSecretRotated":
		return p.applySecretRotated(ctx, event, now)
	case "WebhookSubscriptionAdded":
		return p.applySubscriptionAdded(ctx, event, now)
	case "WebhookSubscriptionRemoved":
		return p.applySubscriptionRemoved(ctx, event)
	default:
		return nil
	}
}

func (p *ConfigProjection) applyEndpointCreated(ctx context.Context, event types.OutboxEvent, now time.Time) error {
	var payload webhookEndpointCreatedPayload
	if err := json.Unmarshal(event.Payload, &payload); err != nil {
		return fmt.Errorf("config projection: decode endpoint created: %w", err)
	}

	endpoint := types.WebhookEndpoint{
		ID:             payload.WebhookID,
		UserID:         payload.UserID,
		UserExternalID: event.UserExternalID,
		Title:          payload.Title,
		URL:            payload.URL,
		Secret:         payload.Secret,
		SecretVersion:  normalisedSecretVersion(payload.SecretVersion),
		IsActive:       payload.Enabled,
	}
	if err := p.store.UpsertEndpoint(ctx, endpoint, now); err != nil {
		return err
	}

	slog.Debug("projected webhook endpoint created", "webhook_id", payload.WebhookID)
	return nil
}

func (p *ConfigProjection) applyEndpointUpdated(ctx context.Context, event types.OutboxEvent, now time.Time) error {
	var payload webhookEndpointUpdatedPayload
	if err := json.Unmarshal(event.Payload, &payload); err != nil {
		return fmt.Errorf("config projection: decode endpoint updated: %w", err)
	}

	return p.store.UpdateEndpoint(
		ctx,
		payload.WebhookID,
		payload.Title,
		payload.URL,
		payload.Enabled,
		now,
	)
}

func (p *ConfigProjection) applyEndpointDeleted(ctx context.Context, event types.OutboxEvent) error {
	var payload webhookEndpointDeletedPayload
	if err := json.Unmarshal(event.Payload, &payload); err != nil {
		return fmt.Errorf("config projection: decode endpoint deleted: %w", err)
	}

	return p.store.DeleteEndpoint(ctx, payload.WebhookID)
}

func (p *ConfigProjection) applySecretRotated(ctx context.Context, event types.OutboxEvent, now time.Time) error {
	var payload webhookSecretRotatedPayload
	if err := json.Unmarshal(event.Payload, &payload); err != nil {
		return fmt.Errorf("config projection: decode secret rotated: %w", err)
	}

	rotation := types.SecretRotation{
		WebhookID:               payload.WebhookID,
		Secret:                  payload.Secret,
		SecretVersion:           normalisedSecretVersion(payload.SecretVersion),
		PreviousSecret:          payload.PreviousSecret,
		PreviousSecretVersion:   payload.PreviousSecretVersion,
		PreviousSecretExpiresAt: payload.PreviousSecretExpiresAt,
	}

	return p.store.RotateSecret(ctx, rotation, now)
}

// normalisedSecretVersion treats an absent version as the first one, so an
// event published before the field existed still projects a usable endpoint.
func normalisedSecretVersion(version int) int {
	if version < 1 {
		return 1
	}

	return version
}

func (p *ConfigProjection) applySubscriptionAdded(ctx context.Context, event types.OutboxEvent, now time.Time) error {
	var payload webhookSubscriptionAddedPayload
	if err := json.Unmarshal(event.Payload, &payload); err != nil {
		return fmt.Errorf("config projection: decode subscription added: %w", err)
	}

	subscription := types.WebhookSubscription{
		ID:        payload.SubscriptionID,
		WebhookID: payload.WebhookID,
		UserID:    payload.UserID,
		EventType: payload.EventType,
	}
	return p.store.AddSubscription(ctx, subscription, now)
}

func (p *ConfigProjection) applySubscriptionRemoved(ctx context.Context, event types.OutboxEvent) error {
	var payload webhookSubscriptionRemovedPayload
	if err := json.Unmarshal(event.Payload, &payload); err != nil {
		return fmt.Errorf("config projection: decode subscription removed: %w", err)
	}

	return p.store.RemoveSubscription(ctx, payload.SubscriptionID)
}
