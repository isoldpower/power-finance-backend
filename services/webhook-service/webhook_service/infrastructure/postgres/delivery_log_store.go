package postgres

import (
	"context"
	"fmt"
	"strings"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"services/webhook-service/webhook_service/types"
)

const deliveryLogColumns = `id, webhook_id, user_id, user_external_id, event_id, event_type,
	target_url, status, attempts, next_attempt_at, last_error, created_at, updated_at`

type DeliveryLogStore struct {
	pool *pgxpool.Pool
}

func NewDeliveryLogStore(pool *pgxpool.Pool) *DeliveryLogStore {
	return &DeliveryLogStore{pool: pool}
}

func (s *DeliveryLogStore) HasDeliveries(ctx context.Context, userExternalID, webhookID string) (bool, error) {
	var exists bool
	scanErr := s.pool.QueryRow(
		ctx,
		`SELECT EXISTS (
			SELECT 1 FROM webhook_deliveries
			WHERE webhook_id = $1 AND user_external_id = $2
		 )`,
		webhookID,
		userExternalID,
	).Scan(&exists)

	if scanErr != nil {
		return false, fmt.Errorf("postgres: delivery existence: %w", scanErr)
	}

	return exists, nil
}

// Count reports how many deliveries match the filters, ignoring the page window.
func (s *DeliveryLogStore) Count(ctx context.Context, query types.DeliveryLogQuery) (int, error) {
	conditions, arguments := filterClause(query)

	var total int
	scanErr := s.pool.QueryRow(
		ctx,
		`SELECT count(*) FROM webhook_deliveries WHERE `+strings.Join(conditions, " AND "),
		arguments...,
	).Scan(&total)

	if scanErr != nil {
		return 0, fmt.Errorf("postgres: count deliveries: %w", scanErr)
	}

	return total, nil
}

// List returns one page plus the lookahead row the cursor minting needs, in the
// API's default order — created_at DESC, id DESC.
func (s *DeliveryLogStore) List(ctx context.Context, query types.DeliveryLogQuery) ([]types.Delivery, error) {
	conditions, arguments := filterClause(query)
	ordering := "created_at DESC, id DESC"

	if query.Anchor != nil {
		comparison := "<"
		if query.Anchor.Backwards {
			comparison = ">"
			ordering = "created_at ASC, id ASC"
		}
		conditions = append(conditions, fmt.Sprintf(
			"(created_at, id) %s ($%d, $%d)",
			comparison,
			len(arguments)+1,
			len(arguments)+2,
		))
		arguments = append(arguments, query.Anchor.CreatedAt, query.Anchor.ID)
	}

	arguments = append(arguments, query.Limit+1)
	statement := fmt.Sprintf(
		`SELECT %s FROM webhook_deliveries WHERE %s ORDER BY %s LIMIT $%d`,
		deliveryLogColumns,
		strings.Join(conditions, " AND "),
		ordering,
		len(arguments),
	)

	rows, queryErr := s.pool.Query(ctx, statement, arguments...)
	if queryErr != nil {
		return nil, fmt.Errorf("postgres: list deliveries: %w", queryErr)
	}
	defer rows.Close()

	deliveries, scanErr := scanDeliveryLogRows(rows)
	if scanErr != nil {
		return nil, scanErr
	}

	if query.Anchor != nil && query.Anchor.Backwards {
		reverseDeliveries(deliveries)
	}

	return deliveries, nil
}

// filterClause builds the always-present ownership predicate plus whichever
// filters the caller supplied, with positional arguments to match.
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
