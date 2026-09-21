package http

import (
	"services/webhook-service/webhook_service/presentation/http/contract"

	"services/webhook-service/webhook_service/types"
)

func paginate(
	rows []types.Delivery,
	query types.DeliveryLogQuery,
) ([]types.Delivery, *string, *string) {
	hasMore := len(rows) > query.Limit
	if hasMore {
		if query.Anchor != nil && query.Anchor.Backwards {
			rows = rows[len(rows)-query.Limit:]
		} else {
			rows = rows[:query.Limit]
		}
	}
	if len(rows) == 0 {
		return rows, nil, nil
	}

	fingerprint := contract.QueryFingerprint(query.Filters, query.WebhookID)
	backwards := query.Anchor != nil && query.Anchor.Backwards

	var nextCursor, previousCursor *string
	if !backwards && hasMore || backwards {
		last := rows[len(rows)-1]
		cursor := contract.EncodeCursor(
			contract.DirectionNext,
			last.CreatedAt,
			last.ID,
			fingerprint,
		)
		nextCursor = &cursor
	}
	if query.Anchor != nil && (!backwards || hasMore) {
		first := rows[0]
		cursor := contract.EncodeCursor(
			contract.DirectionPrevious,
			first.CreatedAt,
			first.ID,
			fingerprint,
		)
		previousCursor = &cursor
	}

	return rows, nextCursor, previousCursor
}

func statusNames() []string {
	names := make([]string, 0, len(types.DeliveryStatuses))
	for _, status := range types.DeliveryStatuses {
		names = append(names, string(status))
	}

	return names
}
