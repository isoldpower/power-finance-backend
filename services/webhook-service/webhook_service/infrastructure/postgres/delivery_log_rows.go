package postgres

import (
	"fmt"

	"github.com/jackc/pgx/v5"

	"services/webhook-service/webhook_service/types"
)

func filterClause(query types.DeliveryLogQuery) ([]string, []any) {
	conditions := []string{"webhook_id = $1", "user_external_id = $2"}
	arguments := []any{query.WebhookID, query.UserExternalID}

	if query.Filters.Status != "" {
		arguments = append(arguments, query.Filters.Status)
		conditions = append(conditions, fmt.Sprintf("status = $%d", len(arguments)))
	}
	if query.Filters.Event != "" {
		arguments = append(arguments, query.Filters.Event)
		conditions = append(conditions, fmt.Sprintf("event_type = $%d", len(arguments)))
	}

	return conditions, arguments
}

func scanDeliveryLogRows(rows pgx.Rows) ([]types.Delivery, error) {
	var deliveries []types.Delivery
	for rows.Next() {
		var delivery types.Delivery
		scanErr := rows.Scan(
			&delivery.ID,
			&delivery.WebhookID,
			&delivery.UserID,
			&delivery.UserExternalID,
			&delivery.EventID,
			&delivery.EventType,
			&delivery.TargetURL,
			&delivery.Status,
			&delivery.Attempts,
			&delivery.NextAttemptAt,
			&delivery.LastError,
			&delivery.CreatedAt,
			&delivery.UpdatedAt,
		)
		if scanErr != nil {
			return nil, fmt.Errorf("postgres: scan delivery log row: %w", scanErr)
		}

		deliveries = append(deliveries, delivery)
	}

	return deliveries, rows.Err()
}

func reverseDeliveries(deliveries []types.Delivery) {
	for left, right := 0, len(deliveries)-1; left < right; left, right = left+1, right-1 {
		deliveries[left], deliveries[right] = deliveries[right], deliveries[left]
	}
}
