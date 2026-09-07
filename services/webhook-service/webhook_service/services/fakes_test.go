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

func (f *fakeDeliveryStore) Reschedule(
	_ context.Context,
	deliveryID string,
	attempts int,
	lastError string,
	nextAttemptAt time.Time,
	_ time.Time,
) error {
	f.rescheduled = append(f.rescheduled, rescheduleCall{
		deliveryID:    deliveryID,
		attempts:      attempts,
		lastError:     lastError,
		nextAttemptAt: nextAttemptAt,
	})
	return nil
}

type fakeSecretResolver struct {
	secret   string
	secrets  types.EndpointSecrets
	err      error
	calls    int
	versions []int
}

func (f *fakeSecretResolver) EndpointSecrets(_ context.Context, _ string) (types.EndpointSecrets, error) {
	f.calls++
	if f.secrets.Secret != "" || f.secrets.PreviousSecret != "" {
		return f.secrets, f.err
	}

	return types.EndpointSecrets{Secret: f.secret, SecretVersion: 1}, f.err
}

type fakeSender struct {
	deliveries []types.Delivery
	secrets    []string
	err        error
}

func (f *fakeSender) Send(_ context.Context, delivery types.Delivery, secret string, _ time.Time) error {
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

func (f *fakeEndpointResolver) ActiveEndpointsForEvent(
	_ context.Context,
	_ int,
	_ string,
) ([]types.WebhookEndpoint, error) {
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
