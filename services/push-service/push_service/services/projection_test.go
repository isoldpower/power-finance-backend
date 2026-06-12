package services

import (
	"testing"
	"time"

	"services/push-service/push_service/types"
)

func validOutboxEvent() types.OutboxEvent {
	return types.OutboxEvent{
		EventID:       "evt-1",
		EventType:     "WalletCreated",
		AggregateType: "wallet",
		UserID:        "user_2abc",
		Payload:       []byte(`{"wallet_id":"wallet-1"}`),
	}
}

func TestProjectionForwardsValidEvents(t *testing.T) {
	projection := NewEventsProjectionService()
	kafkaChannel := make(chan types.OutboxEvent)
	go projection.RunKafkaReceiver(kafkaChannel)

	kafkaChannel <- validOutboxEvent()

	select {
	case projected := <-projection.Events():
		if projected.EventType != "WalletCreated" || string(projected.Payload) == "" {
			t.Fatalf("expected event passthrough, got %+v", projected)
		}
	case <-time.After(time.Second):
		t.Fatal("expected event to be projected")
	}

	close(kafkaChannel)
}

func TestProjectionDropsEventsWithoutEventType(t *testing.T) {
	projection := NewEventsProjectionService()
	kafkaChannel := make(chan types.OutboxEvent)
	go projection.RunKafkaReceiver(kafkaChannel)

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
	go projection.RunKafkaReceiver(kafkaChannel)

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
	go pool.FanoutEvents(eventsChannel)

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
	go pool.FanoutEvents(eventsChannel)

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

func TestCancelledSubscriptionStopsReceivingEvents(t *testing.T) {
	pool := NewClientsPoolService()
	eventsChannel := make(chan types.OutboxEvent)
	go pool.FanoutEvents(eventsChannel)

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
