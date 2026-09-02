package services

import (
	"context"
	"errors"
	"testing"

	"services/webhook-service/webhook_service/types"
)

type fakeDeliveryLogStore struct {
	hasDeliveries bool
	rows          []types.Delivery
	total         int
	err           error
}

func (f *fakeDeliveryLogStore) HasDeliveries(_ context.Context, _, _ string) (bool, error) {
	return f.hasDeliveries, f.err
}

func (f *fakeDeliveryLogStore) Count(_ context.Context, _ types.DeliveryLogQuery) (int, error) {
	return f.total, f.err
}

func (f *fakeDeliveryLogStore) List(_ context.Context, _ types.DeliveryLogQuery) ([]types.Delivery, error) {
	return f.rows, f.err
}

type fakeOwnerResolver struct {
	owner string
	err   error
}

func (f *fakeOwnerResolver) EndpointOwner(_ context.Context, _ string) (string, error) {
	return f.owner, f.err
}

func query() types.DeliveryLogQuery {
	return types.DeliveryLogQuery{UserExternalID: "clerk_7", WebhookID: "wh-1", Limit: 25}
}

func TestOwnerReadsTheirLog(t *testing.T) {
	log := &fakeDeliveryLogStore{rows: []types.Delivery{{ID: "d-1"}}, total: 1}
	service := NewDeliveryLogService(log, &fakeOwnerResolver{owner: "clerk_7"})

	page, err := service.List(context.Background(), query())
	if err != nil {
		t.Fatalf("List returned error: %v", err)
	}
	if page.Total != 1 || len(page.Rows) != 1 {
		t.Fatalf("unexpected page: %+v", page)
	}
}

func TestAnotherUsersEndpointIsNotFound(t *testing.T) {
	service := NewDeliveryLogService(&fakeDeliveryLogStore{}, &fakeOwnerResolver{owner: "clerk_9"})

	if _, err := service.List(context.Background(), query()); !errors.Is(err, ErrWebhookNotFound) {
		t.Fatalf("expected a not-found refusal, got %v", err)
	}
}

// The log outlives its endpoint: deleting a webhook does not delete the history
// its owner may still need to answer "we never received it".
func TestDeletedEndpointStillServesItsLog(t *testing.T) {
	log := &fakeDeliveryLogStore{hasDeliveries: true, rows: []types.Delivery{{ID: "d-1"}}, total: 1}
	service := NewDeliveryLogService(log, &fakeOwnerResolver{owner: ""})

	page, err := service.List(context.Background(), query())
	if err != nil {
		t.Fatalf("List returned error: %v", err)
	}
	if len(page.Rows) != 1 {
		t.Fatalf("expected the surviving log, got %+v", page)
	}
}

func TestUnknownEndpointWithNoHistoryIsNotFound(t *testing.T) {
	service := NewDeliveryLogService(&fakeDeliveryLogStore{}, &fakeOwnerResolver{owner: ""})

	if _, err := service.List(context.Background(), query()); !errors.Is(err, ErrWebhookNotFound) {
		t.Fatalf("expected a not-found refusal, got %v", err)
	}
}
