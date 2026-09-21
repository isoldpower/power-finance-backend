package services

import (
	"context"
	"time"

	"services/webhook-service/webhook_service/types"
)

type fakeConfigStore struct {
	upserted       []types.WebhookEndpoint
	updated        []string
	updatedEnabled []bool
	rotated        []string
	rotations      []types.SecretRotation
	deleted        []string
	addedSubs      []types.WebhookSubscription
	removedSubs    []string
	err            error
}

func (f *fakeConfigStore) UpsertEndpoint(_ context.Context, endpoint types.WebhookEndpoint, _ time.Time) error {
	if f.err != nil {
		return f.err
	}
	f.upserted = append(f.upserted, endpoint)
	return nil
}

func (f *fakeConfigStore) UpdateEndpoint(_ context.Context, webhookID, _, _ string, enabled bool, _ time.Time) error {
	f.updated = append(f.updated, webhookID)
	f.updatedEnabled = append(f.updatedEnabled, enabled)
	return nil
}

func (f *fakeConfigStore) RotateSecret(_ context.Context, rotation types.SecretRotation, _ time.Time) error {
	f.rotated = append(f.rotated, rotation.WebhookID)
	f.rotations = append(f.rotations, rotation)
	return nil
}

func (f *fakeConfigStore) DeleteEndpoint(_ context.Context, webhookID string) error {
	f.deleted = append(f.deleted, webhookID)
	return nil
}

func (f *fakeConfigStore) AddSubscription(
	_ context.Context,
	subscription types.WebhookSubscription,
	_ time.Time,
) error {
	f.addedSubs = append(f.addedSubs, subscription)
	return nil
}

func (f *fakeConfigStore) RemoveSubscription(_ context.Context, subscriptionID string) error {
	f.removedSubs = append(f.removedSubs, subscriptionID)
	return nil
}
