package services

import (
	"bytes"
	"context"
	"errors"
	"testing"

	"services/webhook-service/webhook_service/types"
)

func TestDispatchNonDeliverableEventIsNoOp(t *testing.T) {
	endpoints := &fakeEndpointResolver{}
	store := &fakeDeliveryStore{}
	attempter := &fakeAttempter{}
	dispatcher := NewDeliveryDispatcher(endpoints, store, attempter)

	event := types.OutboxEvent{EventID: "e1", EventType: "WalletCreated", Payload: []byte(`{"user_id":1}`)}
	if err := dispatcher.Dispatch(context.Background(), event); err != nil {
		t.Fatalf("Dispatch returned error: %v", err)
	}

	if endpoints.calls != 0 || len(store.enqueued) != 0 || len(attempter.deliveries) != 0 {
		t.Fatalf("non-deliverable event should do nothing")
	}
}

func TestDispatchFansOutToEverySubscribedEndpoint(t *testing.T) {
	payload := []byte(`{"user_id":7}`)
	endpoints := &fakeEndpointResolver{
		endpoints: []types.WebhookEndpoint{
			{ID: "wh-1", UserID: 7, UserExternalID: "clerk_7", URL: "https://a", Secret: "s1"},
			{ID: "wh-2", UserID: 7, UserExternalID: "clerk_7", URL: "https://b", Secret: "s2"},
		},
	}
	store := &fakeDeliveryStore{}
	attempter := &fakeAttempter{}
	dispatcher := NewDeliveryDispatcher(endpoints, store, attempter)

	event := types.OutboxEvent{EventID: "evt-1", EventType: "TransactionCreated", Payload: payload}
	if err := dispatcher.Dispatch(context.Background(), event); err != nil {
		t.Fatalf("Dispatch returned error: %v", err)
	}

	if len(store.enqueued) != 2 || len(attempter.deliveries) != 2 {
		t.Fatalf("expected 2 enqueues and 2 attempts, got %d/%d", len(store.enqueued), len(attempter.deliveries))
	}

	first := store.enqueued[0]
	if first.WebhookID != "wh-1" || first.TargetURL != "https://a" {
		t.Fatalf("delivery not built from endpoint: %+v", first)
	}
	if first.EventID != "evt-1" || first.EventType != "transaction.created" {
		t.Fatalf("delivery should carry event id and mapped type: %+v", first)
	}
	if !bytes.Equal(first.Payload, payload) {
		t.Fatalf("delivery payload should be the raw event payload")
	}
	if attempter.secrets[0] != "s1" || attempter.secrets[1] != "s2" {
		t.Fatalf("first attempt should use the endpoint secret, got %v", attempter.secrets)
	}
}

func TestDispatchBadPayloadReturnsError(t *testing.T) {
	dispatcher := NewDeliveryDispatcher(&fakeEndpointResolver{}, &fakeDeliveryStore{}, &fakeAttempter{})

	event := types.OutboxEvent{EventID: "e1", EventType: "TransactionCreated", Payload: []byte("not-json")}
	if err := dispatcher.Dispatch(context.Background(), event); err == nil {
		t.Fatalf("expected decode error for malformed payload")
	}
}

func TestDispatchPropagatesResolveError(t *testing.T) {
	endpoints := &fakeEndpointResolver{err: errors.New("db down")}
	dispatcher := NewDeliveryDispatcher(endpoints, &fakeDeliveryStore{}, &fakeAttempter{})

	event := types.OutboxEvent{EventID: "e1", EventType: "TransactionCreated", Payload: []byte(`{"user_id":7}`)}
	if err := dispatcher.Dispatch(context.Background(), event); err == nil {
		t.Fatalf("expected resolve error to propagate")
	}
}

func TestDispatchPropagatesEnqueueError(t *testing.T) {
	endpoints := &fakeEndpointResolver{endpoints: []types.WebhookEndpoint{{ID: "wh-1"}}}
	store := &fakeDeliveryStore{enqueueErr: errors.New("enqueue failed")}
	attempter := &fakeAttempter{}
	dispatcher := NewDeliveryDispatcher(endpoints, store, attempter)

	event := types.OutboxEvent{EventID: "e1", EventType: "TransactionCreated", Payload: []byte(`{"user_id":7}`)}
	if err := dispatcher.Dispatch(context.Background(), event); err == nil {
		t.Fatalf("expected enqueue error to propagate")
	}
	if len(attempter.deliveries) != 0 {
		t.Fatalf("attempt must not run when enqueue fails")
	}
}
