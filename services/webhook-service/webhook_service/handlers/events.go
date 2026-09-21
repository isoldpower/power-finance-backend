package handlers

import (
	"context"

	"services/webhook-service/webhook_service/types"
)

type configProjection interface {
	Handles(eventType string) bool
	Apply(ctx context.Context, event types.OutboxEvent) error
}

type deliveryDispatcher interface {
	Dispatch(ctx context.Context, event types.OutboxEvent) error
}

type retryScheduler interface {
	Run(ctx context.Context)
}

// WebhookHandler routes decoded outbox events to the projection or the dispatcher.
type WebhookHandler struct {
	projection configProjection
	dispatcher deliveryDispatcher
	scheduler  retryScheduler
}

// NewWebhookHandler wires the handler over its projection, dispatcher and scheduler.
func NewWebhookHandler(
	projection configProjection,
	dispatcher deliveryDispatcher,
	scheduler retryScheduler,
) *WebhookHandler {
	return &WebhookHandler{
		projection: projection,
		dispatcher: dispatcher,
		scheduler:  scheduler,
	}
}

// Start launches the retry scheduler, returning a channel closed once it has stopped.
func (h *WebhookHandler) Start(ctx context.Context) <-chan struct{} {
	done := make(chan struct{})
	go func() {
		defer close(done)
		h.scheduler.Run(ctx)
	}()

	return done
}

// Handle routes a decoded outbox event to config projection or delivery dispatch, acknowledging unrelated events.
func (h *WebhookHandler) Handle(ctx context.Context, event types.OutboxEvent) error {
	if h.projection.Handles(event.EventType) {
		return h.projection.Apply(ctx, event)
	}

	if types.WebhookEventTypeFor(event.EventType) != "" {
		return h.dispatcher.Dispatch(ctx, event)
	}

	return nil
}
