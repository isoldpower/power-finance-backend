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

type WebhookHandler struct {
	projection configProjection
	dispatcher deliveryDispatcher
	scheduler  retryScheduler
}

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

// Start launches the background delivery-retry scheduler.
func (h *WebhookHandler) Start(ctx context.Context) {
	go h.scheduler.Run(ctx)
}

// Handle routes a decoded outbox event to config projection or delivery
// dispatch, acknowledging unrelated events.
func (h *WebhookHandler) Handle(ctx context.Context, event types.OutboxEvent) error {
	if h.projection.Handles(event.EventType) {
		return h.projection.Apply(ctx, event)
	}

	if types.WebhookEventTypeFor(event.EventType) != "" {
		return h.dispatcher.Dispatch(ctx, event)
	}

	return nil
}
