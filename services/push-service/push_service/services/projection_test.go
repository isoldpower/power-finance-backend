package services

import (
	"context"
	"testing"
	"time"

	"services/push-service/push_service/services/projections"
	"services/push-service/push_service/types"
)

func validOutboxEvent() types.OutboxEvent {
	return types.OutboxEvent{
		EventID:       "evt-1",
		EventType:     "NotificationCreated",
		AggregateType: "notification",
		UserID:        "user_2abc",
		Payload: []byte(`{
			"notification_id": "notif-1",
			"title": "Visa Credit near limit",
			"body": "You are at 82% of your limit.",
			"severity": "NOTIFICATION_SEVERITY_CRITICAL",
			"subject_type": "wallet",
			"subject_id": "wallet-1",
			"created_at": "2026-08-12T11:51:00Z"
		}`),
	}
}

func TestProjectionForwardsValidEvents(t *testing.T) {
	projection := NewEventsProjectionService()
	kafkaChannel := make(chan types.OutboxEvent)
	go projection.RunKafkaReceiver(context.Background(), kafkaChannel)

	kafkaChannel <- validOutboxEvent()

	select {
	case projected := <-projection.Events():
		if projected.EventType != projections.NotificationCreatedEvent || string(projected.Payload) == "" {
			t.Fatalf("expected a projected notification, got %+v", projected)
		}
	case <-time.After(time.Second):
		t.Fatal("expected event to be projected")
	}

	close(kafkaChannel)
}

// The route is /notifications/stream. Forwarding wallet or transaction frames
// down it would make the endpoint mean something other than its name, so
// anything this stream does not document is dropped rather than passed through.
func TestProjectionDropsEventsItDoesNotDocument(t *testing.T) {
	projection := NewEventsProjectionService()
	kafkaChannel := make(chan types.OutboxEvent)
	go projection.RunKafkaReceiver(context.Background(), kafkaChannel)

	walletEvent := validOutboxEvent()
	walletEvent.EventType = "WalletCreated"
	walletEvent.Payload = []byte(`{"wallet_id":"wallet-1"}`)
	kafkaChannel <- walletEvent
	close(kafkaChannel)

	if _, isOpen := <-projection.Events(); isOpen {
		t.Fatal("expected an undocumented event to be dropped and the channel closed")
	}
}

func TestProjectionDropsEventsWithoutEventType(t *testing.T) {
	projection := NewEventsProjectionService()
	kafkaChannel := make(chan types.OutboxEvent)
	go projection.RunKafkaReceiver(context.Background(), kafkaChannel)

	missingType := validOutboxEvent()
	missingType.EventType = ""
	kafkaChannel <- missingType
	close(kafkaChannel)

	if _, isOpen := <-projection.Events(); isOpen {
		t.Fatal("expected invalid event to be dropped and channel closed")
	}
}

func TestProjectionDropsEventsWithEmptyPayload(t *testing.T) {
	projection := NewEventsProjectionService()
	kafkaChannel := make(chan types.OutboxEvent)
	go projection.RunKafkaReceiver(context.Background(), kafkaChannel)

	emptyPayload := validOutboxEvent()
	emptyPayload.Payload = nil
	kafkaChannel <- emptyPayload
	close(kafkaChannel)

	if _, isOpen := <-projection.Events(); isOpen {
		t.Fatal("expected empty-payload event to be dropped and channel closed")
	}
}

func TestPoolDeliversOnlyToTheEventOwner(t *testing.T) {
	pool := NewClientsPoolService()
	eventsChannel := make(chan types.OutboxEvent)
	go pool.FanoutEvents(context.Background(), eventsChannel)

	ownerClient, registered := pool.Subscribe("user_2abc")
	if !registered {
		t.Fatal("expected owner client to subscribe")
	}
	strangerClient, registered := pool.Subscribe("user_other")
	if !registered {
		t.Fatal("expected stranger client to subscribe")
	}

	eventsChannel <- validOutboxEvent()

	select {
	case received := <-ownerClient.Events():
		if received.EventID != "evt-1" {
			t.Fatalf("expected evt-1, got %+v", received)
		}
	case <-time.After(time.Second):
		t.Fatal("expected event to reach its owner")
	}

	select {
	case leaked := <-strangerClient.Events():
		t.Fatalf("expected no delivery to another user, got %+v", leaked)
	case <-time.After(50 * time.Millisecond):
	}

	close(eventsChannel)
}

func TestPoolBroadcastsGlobalEventsToEverySubscriber(t *testing.T) {
	pool := NewClientsPoolService()
	eventsChannel := make(chan types.OutboxEvent)
	go pool.FanoutEvents(context.Background(), eventsChannel)

	firstClient, registered := pool.Subscribe("user_2abc")
	if !registered {
		t.Fatal("expected first client to subscribe")
	}
	secondClient, registered := pool.Subscribe("user_other")
	if !registered {
		t.Fatal("expected second client to subscribe")
	}

	globalEvent := validOutboxEvent()
	globalEvent.UserID = types.GlobalPartitionKey
	eventsChannel <- globalEvent

	for _, client := range []types.ClientSubscription{firstClient, secondClient} {
		select {
		case received := <-client.Events():
			if received.EventID != "evt-1" {
				t.Fatalf("expected evt-1, got %+v", received)
			}
		case <-time.After(time.Second):
			t.Fatal("expected global broadcast to reach every client")
		}
	}

	close(eventsChannel)
}

func TestProjectionStopsOnContextCancel(t *testing.T) {
	projection := NewEventsProjectionService()
	ctx, cancel := context.WithCancel(context.Background())
	kafkaChannel := make(chan types.OutboxEvent)

	done := make(chan struct{})
	go func() {
		projection.RunKafkaReceiver(ctx, kafkaChannel)
		close(done)
	}()

	cancel()

	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("expected projection receiver to stop on context cancel")
	}

	if _, isOpen := <-projection.Events(); isOpen {
		t.Fatal("expected events channel to be closed after shutdown")
	}
}

func TestFanoutStopsAndDetachesClientsOnContextCancel(t *testing.T) {
	pool := NewClientsPoolService()
	ctx, cancel := context.WithCancel(context.Background())
	eventsChannel := make(chan types.OutboxEvent)

	done := make(chan struct{})
	go func() {
		pool.FanoutEvents(ctx, eventsChannel)
		close(done)
	}()

	subscription, registered := pool.Subscribe("user_2abc")
	if !registered {
		t.Fatal("expected client to subscribe before shutdown")
	}

	cancel()

	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("expected fanout to stop on context cancel")
	}

	if _, isOpen := <-subscription.Events(); isOpen {
		t.Fatal("expected subscriber channel to close on shutdown")
	}
	if _, registered := pool.Subscribe("user_late"); registered {
		t.Fatal("expected subscribe to fail after shutdown")
	}
}

func TestCancelledSubscriptionStopsReceivingEvents(t *testing.T) {
	pool := NewClientsPoolService()
	eventsChannel := make(chan types.OutboxEvent)
	go pool.FanoutEvents(context.Background(), eventsChannel)

	subscription, registered := pool.Subscribe("user_2abc")
	if !registered {
		t.Fatal("expected client to subscribe")
	}

	subscription.Cancel()

	select {
	case _, isOpen := <-subscription.Events():
		if isOpen {
			t.Fatal("expected cancelled subscription channel to be closed")
		}
	case <-time.After(time.Second):
		t.Fatal("expected cancelled subscription channel to close")
	}

	close(eventsChannel)
}
