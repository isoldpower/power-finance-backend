package http

import (
	"services/webhook-service/webhook_service/presentation/http/contract"
	"time"

	"services/webhook-service/webhook_service/types"
)

// presentDelivery renders one log row.
func presentDelivery(delivery types.Delivery) map[string]any {
	return map[string]any{
		"id":              delivery.ID,
		"created_at":      delivery.CreatedAt.Format(contract.IsoLayout),
		"updated_at":      optionalTime(&delivery.UpdatedAt),
		"webhook_id":      delivery.WebhookID,
		"event_id":        delivery.EventID,
		"event":           delivery.EventType,
		"target_url":      delivery.TargetURL,
		"status":          string(delivery.Status),
		"attempts":        delivery.Attempts,
		"next_attempt_at": optionalTime(delivery.NextAttemptAt),
		"last_error":      optionalText(delivery.LastError),
	}
}

func presentDeliveries(deliveries []types.Delivery) []map[string]any {
	presented := make([]map[string]any, 0, len(deliveries))
	for _, delivery := range deliveries {
		presented = append(presented, presentDelivery(delivery))
	}

	return presented
}

func optionalTime(moment *time.Time) any {
	if moment == nil || moment.IsZero() {
		return nil
	}

	return moment.Format(contract.IsoLayout)
}

func optionalText(value string) any {
	if value == "" {
		return nil
	}

	return value
}
