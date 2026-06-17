package handlers

import (
	"context"
	"testing"
	"time"

	"services/webhook-service/webhook_service/types"
)

type fakeProjection struct {
	handled map[string]bool
	applied []types.OutboxEvent
}

func (f *fakeProjection) Handles(eventType string) bool {
	return f.handled[eventType]
}

func (f *fakeProjection) Apply(_ context.Context, event types.OutboxEvent) error {
	f.applied = append(f.applied, event)
	return nil
}

type fakeDispatcher struct {
	dispatched []types.OutboxEvent
}

func (f *fakeDispatcher) Dispatch(_ context.Context, event types.OutboxEvent) error {
	f.dispatched = append(f.dispatched, event)
	return nil
}

type fakeScheduler struct {
	started chan struct{}
}

func (f *fakeScheduler) Run(_ context.Context) {
	close(f.started)
}

func TestHandleRoutesConfigEventToProjection(t *testing.T) {
	projection := &fakeProjection{handled: map[string]bool{"WebhookEndpointCreated": true}}
	dispatcher := &fakeDispatcher{}
	handler := NewWebhookHandler(projection, dispatcher, &fakeScheduler{})

	event := types.OutboxEvent{EventType: "WebhookEndpointCreated"}
	if err := handler.Handle(context.Background(), event); err != nil {
		t.Fatalf("Handle returned error: %v", err)
	}

	if len(projection.applied) != 1 {
		t.Fatalf("config event should hit projection, got %d", len(projection.applied))
	}
	if len(dispatcher.dispatched) != 0 {
		t.Fatalf("config event must not enter dispatch")
	}
}

func TestHandleRoutesDomainEventToDispatcher(t *testing.T) {
	projection := &fakeProjection{handled: map[string]bool{}}
	dispatcher := &fakeDispatcher{}
	handler := NewWebhookHandler(projection, dispatcher, &fakeScheduler{})

	event := types.OutboxEvent{EventType: "TransactionCreated"}
	if err := handler.Handle(context.Background(), event); err != nil {
		t.Fatalf("Handle returned error: %v", err)
	}

	if len(dispatcher.dispatched) != 1 {
		t.Fatalf("domain event should reach dispatcher, got %d", len(dispatcher.dispatched))
	}
	if len(projection.applied) != 0 {
		t.Fatalf("domain event must not touch projection")
	}
}

func TestHandleIgnoresUnrelatedEvent(t *testing.T) {
	projection := &fakeProjection{handled: map[string]bool{}}
	dispatcher := &fakeDispatcher{}
	handler := NewWebhookHandler(projection, dispatcher, &fakeScheduler{})

	event := types.OutboxEvent{EventType: "WalletCreated"}
	if err := handler.Handle(context.Background(), event); err != nil {
		t.Fatalf("Handle returned error: %v", err)
	}

	if len(projection.applied) != 0 || len(dispatcher.dispatched) != 0 {
		t.Fatalf("unrelated event should be acked with no work")
	}
}

func TestStartLaunchesScheduler(t *testing.T) {
	scheduler := &fakeScheduler{started: make(chan struct{})}
	handler := NewWebhookHandler(&fakeProjection{}, &fakeDispatcher{}, scheduler)

	handler.Start(context.Background())

	select {
	case <-scheduler.started:
	case <-time.After(time.Second):
		t.Fatal("Start did not launch the scheduler")
	}
}
