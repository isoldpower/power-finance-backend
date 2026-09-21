package services

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"services/webhook-service/webhook_service/types"
)

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

	logEndpointProjected(payload.WebhookID)
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
