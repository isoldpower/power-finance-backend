package services

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"time"

	"services/webhook-service/webhook_service/types"
)

type endpointResolver interface {
	ActiveEndpointsForEvent(ctx context.Context, userID int, eventType string) ([]types.WebhookEndpoint, error)
}

type deliveryAttempter interface {
	Attempt(ctx context.Context, delivery types.Delivery, secret string) error
}

type DeliveryDispatcher struct {
	endpoints  endpointResolver
	deliveries deliveryStore
	attempter  deliveryAttempter
}

func NewDeliveryDispatcher(
	endpoints endpointResolver,
	deliveries deliveryStore,
	attempter deliveryAttempter,
) *DeliveryDispatcher {
	return &DeliveryDispatcher{
		endpoints:  endpoints,
		deliveries: deliveries,
		attempter:  attempter,
	}
}

// Dispatch fans the event out to every subscribed endpoint, durably
// enqueueing each delivery and running the first attempt inline.
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

		if attemptErr := d.attempter.Attempt(ctx, delivery, endpoint.Secret); attemptErr != nil {
			slog.Error(
				"webhook first-attempt bookkeeping failed",
				"delivery_id", delivery.ID,
				"error", attemptErr,
			)
			return attemptErr
		}
	}

	return nil
}
