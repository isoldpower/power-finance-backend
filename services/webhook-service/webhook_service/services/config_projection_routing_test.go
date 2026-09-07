package services

import (
	"context"
	"testing"

	"services/webhook-service/webhook_service/types"
)

func TestApplyRoutesEachConfigEvent(t *testing.T) {
	cases := []struct {
		name    string
		event   types.OutboxEvent
		observe func(*fakeConfigStore) int
	}{
		{
			name: "updated",
			event: types.OutboxEvent{
				EventType: "WebhookEndpointUpdated",
				Payload:   []byte(`{"webhook_id":"wh-1","title":"t","url":"u","enabled":true}`),
			},
			observe: func(s *fakeConfigStore) int { return len(s.updated) },
		},
		{
			name: "deleted",
			event: types.OutboxEvent{
				EventType: "WebhookEndpointDeleted",
				Payload:   []byte(`{"webhook_id":"wh-1"}`),
			},
			observe: func(s *fakeConfigStore) int { return len(s.deleted) },
		},
		{
			name: "secret rotated",
			event: types.OutboxEvent{
				EventType: "WebhookSecretRotated",
				Payload:   []byte(`{"webhook_id":"wh-1","secret":"new"}`),
			},
			observe: func(s *fakeConfigStore) int { return len(s.rotated) },
		},
		{
			name: "subscription added",
			event: types.OutboxEvent{
				EventType: "WebhookSubscriptionAdded",
				Payload: []byte(
					`{"subscription_id":"sub-1","webhook_id":"wh-1",` +
						`"user_id":1,"event_type":"transaction.created"}`,
				),
			},
			observe: func(s *fakeConfigStore) int { return len(s.addedSubs) },
		},
		{
			name: "subscription removed",
			event: types.OutboxEvent{
				EventType: "WebhookSubscriptionRemoved",
				Payload:   []byte(`{"subscription_id":"sub-1"}`),
			},
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
