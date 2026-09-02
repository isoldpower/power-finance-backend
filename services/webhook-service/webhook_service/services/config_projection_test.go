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
		Payload:        []byte(`{"webhook_id":"wh-1","user_id":9,"title":"t","url":"https://x","secret":"sec","secret_version":1,"enabled":true}`),
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
	if endpoint.SecretVersion != 1 {
		t.Fatalf("created endpoint should carry its secret version: %+v", endpoint)
	}
}

// An endpoint registered with enabled:false must not receive, so the pause
// switch has to survive the projection rather than defaulting to on.
func TestApplyEndpointCreatedHonoursDisabled(t *testing.T) {
	store := &fakeConfigStore{}
	projection := NewConfigProjection(store)

	event := types.OutboxEvent{
		EventType: "WebhookEndpointCreated",
		Payload:   []byte(`{"webhook_id":"wh-1","user_id":9,"url":"https://x","secret":"s","enabled":false}`),
	}
	if err := projection.Apply(context.Background(), event); err != nil {
		t.Fatalf("Apply returned error: %v", err)
	}

	if store.upserted[0].IsActive {
		t.Fatalf("a disabled endpoint must not project as active")
	}
}

// An event published before secret_version existed still has to yield a usable
// endpoint rather than one pinned to version zero.
func TestApplyEndpointCreatedDefaultsSecretVersion(t *testing.T) {
	store := &fakeConfigStore{}
	projection := NewConfigProjection(store)

	event := types.OutboxEvent{
		EventType: "WebhookEndpointCreated",
		Payload:   []byte(`{"webhook_id":"wh-1","user_id":9,"url":"https://x","secret":"s","enabled":true}`),
	}
	if err := projection.Apply(context.Background(), event); err != nil {
		t.Fatalf("Apply returned error: %v", err)
	}

	if store.upserted[0].SecretVersion != 1 {
		t.Fatalf("expected secret version 1, got %d", store.upserted[0].SecretVersion)
	}
}

// The grace window is the whole point of rotation: the replaced secret and its
// expiry have to reach the store, not just the new secret.
func TestApplySecretRotatedCarriesTheGraceWindow(t *testing.T) {
	store := &fakeConfigStore{}
	projection := NewConfigProjection(store)

	event := types.OutboxEvent{
		EventType: "WebhookSecretRotated",
		Payload: []byte(`{"webhook_id":"wh-1","secret":"new","secret_version":2,` +
			`"previous_secret":"old","previous_secret_version":1,` +
			`"previous_secret_expires_at":"2026-09-03T07:00:00Z"}`),
	}
	if err := projection.Apply(context.Background(), event); err != nil {
		t.Fatalf("Apply returned error: %v", err)
	}

	rotation := store.rotations[0]
	if rotation.Secret != "new" || rotation.SecretVersion != 2 {
		t.Fatalf("new secret not projected: %+v", rotation)
	}
	if rotation.PreviousSecret != "old" || rotation.PreviousSecretVersion != 1 {
		t.Fatalf("replaced secret not projected: %+v", rotation)
	}
	if rotation.PreviousSecretExpiresAt == nil {
		t.Fatalf("grace window expiry not projected: %+v", rotation)
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
			event:   types.OutboxEvent{EventType: "WebhookEndpointUpdated", Payload: []byte(`{"webhook_id":"wh-1","title":"t","url":"u","enabled":true}`)},
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
