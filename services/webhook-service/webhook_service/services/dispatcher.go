package services

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"services/webhook-service/webhook_service/types"
)

type endpointResolver interface {
	ActiveEndpointsForEvent(ctx context.Context, userID int, eventType string) ([]types.WebhookEndpoint, error)
}

// deliveryWaker is signalled after new deliveries are enqueued so the scheduler
// can attempt them promptly instead of waiting for its next tick.
type deliveryWaker interface {
	Wake()
}

type DeliveryDispatcher struct {
	endpoints  endpointResolver
	deliveries deliveryStore
	waker      deliveryWaker
}

func NewDeliveryDispatcher(
	endpoints endpointResolver,
	deliveries deliveryStore,
	waker deliveryWaker,
) *DeliveryDispatcher {
	return &DeliveryDispatcher{
		endpoints:  endpoints,
		deliveries: deliveries,
		waker:      waker,
	}
}

// Dispatch fans the event out to every subscribed endpoint by durably enqueueing
// a delivery and waking the scheduler. The HTTP attempts themselves run off the
// consumer path in the scheduler, so a slow endpoint cannot stall consumption.
func (d *DeliveryDispatcher) Dispatch(ctx context.Context, event types.OutboxEvent) error {
	webhookEventType := types.WebhookEventTypeFor(event.EventType)
	if webhookEventType == "" {
		return nil
	}

	var payload domainEventPayload
	if err := json.Unmarshal(event.Payload, &payload); err != nil {
		return fmt.Errorf("dispatcher: decode domain event: %w", err)
	}

	endpoints, resolveErr := d.endpoints.ActiveEndpointsForEvent(ctx, payload.UserID, webhookEventType)
	if resolveErr != nil {
		return resolveErr
	}

	now := time.Now().UTC()
	for _, endpoint := range endpoints {
		delivery := types.Delivery{
			ID:             newUUID(),
			WebhookID:      endpoint.ID,
			UserID:         endpoint.UserID,
			UserExternalID: endpoint.UserExternalID,
			EventID:        event.EventID,
			EventType:      webhookEventType,
			TargetURL:      endpoint.URL,
			Payload:        event.Payload,
			Status:         types.DeliveryPending,
		}

		if enqueueErr := d.deliveries.Enqueue(ctx, delivery, now); enqueueErr != nil {
			return enqueueErr
		}
		d.waker.Wake()
	}

	return nil
}
