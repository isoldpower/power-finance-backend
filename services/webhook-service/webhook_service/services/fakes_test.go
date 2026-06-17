package services

import (
	"context"
	"time"

	"services/webhook-service/webhook_service/types"
)

type fakeDeliveryStore struct {
	enqueued    []types.Delivery
	succeeded   []string
	failed      []string
	rescheduled []rescheduleCall

	claimDue   []types.Delivery
	claimErr   error
	enqueueErr error
}

type rescheduleCall struct {
	deliveryID    string
	attempts      int
	lastError     string
	nextAttemptAt time.Time
}

func (f *fakeDeliveryStore) Enqueue(_ context.Context, delivery types.Delivery, _ time.Time) error {
	if f.enqueueErr != nil {
		return f.enqueueErr
	}
	f.enqueued = append(f.enqueued, delivery)
	return nil
}

func (f *fakeDeliveryStore) ClaimDue(_ context.Context, _ time.Time, _ time.Duration, _ int) ([]types.Delivery, error) {
	return f.claimDue, f.claimErr
}

func (f *fakeDeliveryStore) MarkSucceeded(_ context.Context, deliveryID string, _ int, _ time.Time) error {
	f.succeeded = append(f.succeeded, deliveryID)
	return nil
}

func (f *fakeDeliveryStore) MarkFailed(_ context.Context, deliveryID string, _ int, _ string, _ time.Time) error {
	f.failed = append(f.failed, deliveryID)
	return nil
}

func (f *fakeDeliveryStore) Reschedule(_ context.Context, deliveryID string, attempts int, lastError string, nextAttemptAt time.Time, _ time.Time) error {
	f.rescheduled = append(f.rescheduled, rescheduleCall{
		deliveryID:    deliveryID,
		attempts:      attempts,
		lastError:     lastError,
		nextAttemptAt: nextAttemptAt,
	})
	return nil
}

type fakeSecretResolver struct {
	secret string
	err    error
	calls  int
}

func (f *fakeSecretResolver) EndpointSecret(_ context.Context, _ string) (string, error) {
	f.calls++
	return f.secret, f.err
}

type fakeSender struct {
	deliveries []types.Delivery
	secrets    []string
	err        error
}

func (f *fakeSender) Send(_ context.Context, delivery types.Delivery, secret string) error {
	f.deliveries = append(f.deliveries, delivery)
	f.secrets = append(f.secrets, secret)
	return f.err
}

type fakeNotifier struct {
	calls []notifyCall
	err   error
}

type notifyCall struct {
	delivery types.Delivery
	short    string
	message  string
}

func (f *fakeNotifier) RequestNotification(_ context.Context, delivery types.Delivery, short, message string) error {
	f.calls = append(f.calls, notifyCall{delivery: delivery, short: short, message: message})
	return f.err
}

type fakeEndpointResolver struct {
	endpoints []types.WebhookEndpoint
	err       error
	calls     int
}

func (f *fakeEndpointResolver) ActiveEndpointsForEvent(_ context.Context, _ int, _ string) ([]types.WebhookEndpoint, error) {
	f.calls++
	return f.endpoints, f.err
}

type fakeAttempter struct {
	deliveries []types.Delivery
	secrets    []string
	err        error
}

func (f *fakeAttempter) Attempt(_ context.Context, delivery types.Delivery, secret string) error {
	f.deliveries = append(f.deliveries, delivery)
	f.secrets = append(f.secrets, secret)
	return f.err
}

type fakeWaker struct {
	wakes int
}

func (f *fakeWaker) Wake() { f.wakes++ }

// signalingAttempter reports each attempt over a channel so Run-driven tests can
// observe deliveries without racing on a shared slice.
type signalingAttempter struct {
	attempted chan types.Delivery
}

func (s *signalingAttempter) Attempt(_ context.Context, delivery types.Delivery, _ string) error {
	s.attempted <- delivery
	return nil
}

type fakeConfigStore struct {
	upserted    []types.WebhookEndpoint
	updated     []string
	rotated     []string
	deleted     []string
	addedSubs   []types.WebhookSubscription
	removedSubs []string
	err         error
}

func (f *fakeConfigStore) UpsertEndpoint(_ context.Context, endpoint types.WebhookEndpoint, _ time.Time) error {
	if f.err != nil {
		return f.err
	}
	f.upserted = append(f.upserted, endpoint)
	return nil
}

func (f *fakeConfigStore) UpdateEndpoint(_ context.Context, webhookID, _, _ string, _ time.Time) error {
	f.updated = append(f.updated, webhookID)
	return nil
}

func (f *fakeConfigStore) RotateSecret(_ context.Context, webhookID, _ string, _ time.Time) error {
	f.rotated = append(f.rotated, webhookID)
	return nil
}

func (f *fakeConfigStore) DeleteEndpoint(_ context.Context, webhookID string) error {
	f.deleted = append(f.deleted, webhookID)
	return nil
}

func (f *fakeConfigStore) AddSubscription(_ context.Context, subscription types.WebhookSubscription, _ time.Time) error {
	f.addedSubs = append(f.addedSubs, subscription)
	return nil
}

func (f *fakeConfigStore) RemoveSubscription(_ context.Context, subscriptionID string) error {
	f.removedSubs = append(f.removedSubs, subscriptionID)
	return nil
}
