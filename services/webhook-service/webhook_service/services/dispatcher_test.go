package services

import (
	"context"
	"encoding/json"
	"errors"
	"testing"

	"services/webhook-service/webhook_service/types"
)

func TestDispatchNonDeliverableEventIsNoOp(t *testing.T) {
	endpoints := &fakeEndpointResolver{}
	store := &fakeDeliveryStore{}
	waker := &fakeWaker{}
	dispatcher := NewDeliveryDispatcher(endpoints, store, waker)

	event := types.OutboxEvent{EventID: "e1", EventType: "GoalCreated", Payload: []byte(`{"user_id":1}`)}
	if err := dispatcher.Dispatch(context.Background(), event); err != nil {
		t.Fatalf("Dispatch returned error: %v", err)
	}

	if endpoints.calls != 0 || len(store.enqueued) != 0 || waker.wakes != 0 {
		t.Fatalf("non-deliverable event should do nothing")
	}
}

func TestDispatchEnqueuesAndWakesForEverySubscribedEndpoint(t *testing.T) {
	payload := []byte(`{"event_id":"evt-1","occurred_at":"2026-08-12T11:51:00Z","schema_version":1,"user_id":7,"name":"Coffee"}`)
	endpoints := &fakeEndpointResolver{
		endpoints: []types.WebhookEndpoint{
			{ID: "wh-1", UserID: 7, UserExternalID: "clerk_7", URL: "https://a", Secret: "s1", SecretVersion: 3},
			{ID: "wh-2", UserID: 7, UserExternalID: "clerk_7", URL: "https://b", Secret: "s2", SecretVersion: 1},
		},
	}
	store := &fakeDeliveryStore{}
	waker := &fakeWaker{}
	dispatcher := NewDeliveryDispatcher(endpoints, store, waker)

	event := types.OutboxEvent{EventID: "evt-1", EventType: "TransactionCreated", Payload: payload}
	if err := dispatcher.Dispatch(context.Background(), event); err != nil {
		t.Fatalf("Dispatch returned error: %v", err)
	}

	if len(store.enqueued) != 2 || waker.wakes != 2 {
		t.Fatalf("expected 2 enqueues and 2 wakes, got %d/%d", len(store.enqueued), waker.wakes)
	}

	first := store.enqueued[0]
	if first.WebhookID != "wh-1" || first.TargetURL != "https://a" {
		t.Fatalf("delivery not built from endpoint: %+v", first)
	}
	if first.EventID != "evt-1" || first.EventType != "transaction.created" {
		t.Fatalf("delivery should carry event id and mapped type: %+v", first)
	}
	if first.Status != types.DeliveryPending {
		t.Fatalf("delivery should be enqueued pending: %+v", first)
	}
	if first.SecretVersion != 3 {
		t.Fatalf("delivery should pin the endpoint's current secret version: %+v", first)
	}

	var body map[string]any
	if err := json.Unmarshal(first.Payload, &body); err != nil {
		t.Fatalf("delivery body is not JSON: %v", err)
	}
	if body["id"] != "evt-1" || body["event"] != "transaction.created" {
		t.Fatalf("delivery body envelope not built: %+v", body)
	}
	if body["created_at"] != "2026-08-12T11:51:00Z" {
		t.Fatalf("delivery body should carry the event's occurred_at: %+v", body)
	}

	data, isObject := body["data"].(map[string]any)
	if !isObject {
		t.Fatalf("delivery body should carry the subject under data: %+v", body)
	}
	if data["name"] != "Coffee" {
		t.Fatalf("subject fields should survive into data: %+v", data)
	}
	for _, field := range envelopeFields {
		if _, present := data[field]; present {
			t.Fatalf("outbox bookkeeping %q must not leak into data: %+v", field, data)
		}
	}
}

func TestDispatchBadPayloadReturnsError(t *testing.T) {
	dispatcher := NewDeliveryDispatcher(&fakeEndpointResolver{}, &fakeDeliveryStore{}, &fakeWaker{})

	event := types.OutboxEvent{EventID: "e1", EventType: "TransactionCreated", Payload: []byte("not-json")}
	if err := dispatcher.Dispatch(context.Background(), event); err == nil {
		t.Fatalf("expected decode error for malformed payload")
	}
}

func TestDispatchPropagatesResolveError(t *testing.T) {
	endpoints := &fakeEndpointResolver{err: errors.New("db down")}
	dispatcher := NewDeliveryDispatcher(endpoints, &fakeDeliveryStore{}, &fakeWaker{})

	event := types.OutboxEvent{EventID: "e1", EventType: "TransactionCreated", Payload: []byte(`{"user_id":7}`)}
	if err := dispatcher.Dispatch(context.Background(), event); err == nil {
		t.Fatalf("expected resolve error to propagate")
	}
}

func TestDispatchPropagatesEnqueueError(t *testing.T) {
	endpoints := &fakeEndpointResolver{endpoints: []types.WebhookEndpoint{{ID: "wh-1"}}}
	store := &fakeDeliveryStore{enqueueErr: errors.New("enqueue failed")}
	waker := &fakeWaker{}
	dispatcher := NewDeliveryDispatcher(endpoints, store, waker)

	event := types.OutboxEvent{EventID: "e1", EventType: "TransactionCreated", Payload: []byte(`{"user_id":7}`)}
	if err := dispatcher.Dispatch(context.Background(), event); err == nil {
		t.Fatalf("expected enqueue error to propagate")
	}
	if waker.wakes != 0 {
		t.Fatalf("scheduler must not be woken when enqueue fails")
	}
}
