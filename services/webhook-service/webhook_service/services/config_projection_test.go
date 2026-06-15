package services

import (
	"context"
	"testing"

	"services/webhook-service/webhook_service/types"
)

func TestConfigProjectionHandles(t *testing.T) {
	projection := NewConfigProjection(&fakeConfigStore{})

	owned := []string{
		"WebhookEndpointCreated",
		"WebhookEndpointUpdated",
		"WebhookEndpointDeleted",
		"WebhookSecretRotated",
		"WebhookSubscriptionAdded",
		"WebhookSubscriptionRemoved",
	}
	for _, eventType := range owned {
		if !projection.Handles(eventType) {
			t.Errorf("expected projection to own %q", eventType)
		}
	}
	if projection.Handles("TransactionCreated") {
		t.Errorf("projection should not own domain events")
	}
}

func TestApplyEndpointCreatedUpserts(t *testing.T) {
	store := &fakeConfigStore{}
	projection := NewConfigProjection(store)

	event := types.OutboxEvent{
		EventType:      "WebhookEndpointCreated",
		UserExternalID: "clerk_9",
		Payload:        []byte(`{"webhook_id":"wh-1","user_id":9,"title":"t","url":"https://x","secret":"sec"}`),
	}
	if err := projection.Apply(context.Background(), event); err != nil {
		t.Fatalf("Apply returned error: %v", err)
	}

	if len(store.upserted) != 1 {
		t.Fatalf("expected one upsert, got %d", len(store.upserted))
	}
	endpoint := store.upserted[0]
	if endpoint.ID != "wh-1" || endpoint.UserExternalID != "clerk_9" || endpoint.Secret != "sec" {
		t.Fatalf("upserted endpoint not populated from payload + event: %+v", endpoint)
	}
	if !endpoint.IsActive {
		t.Fatalf("created endpoint should be active")
	}
}

func TestApplyRoutesEachConfigEvent(t *testing.T) {
	cases := []struct {
		name    string
		event   types.OutboxEvent
		observe func(*fakeConfigStore) int
	}{
		{
			name:    "updated",
			event:   types.OutboxEvent{EventType: "WebhookEndpointUpdated", Payload: []byte(`{"webhook_id":"wh-1","title":"t","url":"u"}`)},
			observe: func(s *fakeConfigStore) int { return len(s.updated) },
		},
		{
			name:    "deleted",
			event:   types.OutboxEvent{EventType: "WebhookEndpointDeleted", Payload: []byte(`{"webhook_id":"wh-1"}`)},
			observe: func(s *fakeConfigStore) int { return len(s.deleted) },
		},
		{
			name:    "secret rotated",
			event:   types.OutboxEvent{EventType: "WebhookSecretRotated", Payload: []byte(`{"webhook_id":"wh-1","secret":"new"}`)},
			observe: func(s *fakeConfigStore) int { return len(s.rotated) },
		},
		{
			name:    "subscription added",
			event:   types.OutboxEvent{EventType: "WebhookSubscriptionAdded", Payload: []byte(`{"subscription_id":"sub-1","webhook_id":"wh-1","user_id":1,"event_type":"transaction.created"}`)},
			observe: func(s *fakeConfigStore) int { return len(s.addedSubs) },
		},
		{
			name:    "subscription removed",
			event:   types.OutboxEvent{EventType: "WebhookSubscriptionRemoved", Payload: []byte(`{"subscription_id":"sub-1"}`)},
			observe: func(s *fakeConfigStore) int { return len(s.removedSubs) },
		},
	}

	for _, testCase := range cases {
		t.Run(testCase.name, func(t *testing.T) {
			store := &fakeConfigStore{}
			projection := NewConfigProjection(store)

			if err := projection.Apply(context.Background(), testCase.event); err != nil {
				t.Fatalf("Apply returned error: %v", err)
			}
			if testCase.observe(store) != 1 {
				t.Fatalf("expected the matching store method to be called once")
			}
		})
	}
}

func TestApplyMalformedPayloadReturnsError(t *testing.T) {
	projection := NewConfigProjection(&fakeConfigStore{})

	event := types.OutboxEvent{EventType: "WebhookEndpointCreated", Payload: []byte("nope")}
	if err := projection.Apply(context.Background(), event); err == nil {
		t.Fatalf("expected decode error for malformed payload")
	}
}
