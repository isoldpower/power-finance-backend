package services

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"services/webhook-service/webhook_service/types"
)

type endpointResolver interface {
	ActiveEndpointsForEvent(
		ctx context.Context,
		userID int,
		eventType string,
	) ([]types.WebhookEndpoint, error)
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
// a delivery and waking the scheduler.
func (d *DeliveryDispatcher) Dispatch(ctx context.Context, event types.OutboxEvent) error {
	webhookEventType := types.WebhookEventTypeFor(event.EventType)
	if webhookEventType == "" {
		return nil
	}

	var payload domainEventPayload
	if err := json.Unmarshal(event.Payload, &payload); err != nil {
		return fmt.Errorf("dispatcher: decode domain event: %w", err)
	}

	endpoints, resolveErr := d.endpoints.ActiveEndpointsForEvent(
		ctx,
		payload.UserID,
		webhookEventType,
	)
	if resolveErr != nil {
		return resolveErr
	}
	if len(endpoints) == 0 {
		return nil
	}

	body, bodyErr := buildDeliveryBody(event, webhookEventType)
	if bodyErr != nil {
		return bodyErr
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
			Payload:        body,
			SecretVersion:  endpoint.SecretVersion,
			Status:         types.DeliveryPending,
		}

		if enqueueErr := d.deliveries.Enqueue(ctx, delivery, now); enqueueErr != nil {
			return enqueueErr
		}
		d.waker.Wake()
	}

	return nil
}

// envelopeFields are the outbox event's own bookkeeping.
var envelopeFields = []string{"event_id", "occurred_at", "schema_version"}

// buildDeliveryBody wraps the domain event in the envelope the receiver's code
// is written against.
func buildDeliveryBody(event types.OutboxEvent, webhookEventType string) ([]byte, error) {
	var decoded map[string]any
	if err := json.Unmarshal(event.Payload, &decoded); err != nil {
		return nil, fmt.Errorf("dispatcher: decode delivery payload: %w", err)
	}

	occurredAt, _ := decoded["occurred_at"].(string)
	for _, field := range envelopeFields {
		delete(decoded, field)
	}

	body, marshalErr := json.Marshal(map[string]any{
		"id":         event.EventID,
		"event":      webhookEventType,
		"created_at": occurredAt,
		"data":       decoded,
	})
	if marshalErr != nil {
		return nil, fmt.Errorf("dispatcher: encode delivery payload: %w", marshalErr)
	}

	return body, nil
}
