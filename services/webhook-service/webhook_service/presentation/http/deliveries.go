package http

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"strconv"
	"strings"

	"services/webhook-service/webhook_service/services"
	"services/webhook-service/webhook_service/types"
)

const (
	defaultLimit = 25
	maximumLimit = 100
	minimumLimit = 1

	limitParam  = "limit"
	cursorParam = "cursor"
	statusParam = "status"
	eventParam  = "event"
)

type deliveryLogReader interface {
	List(ctx context.Context, query types.DeliveryLogQuery) (types.DeliveryLogPage, error)
}

// handleDeliveryLog answers GET /api/v1/webhooks/{id}/deliveries. The log lives
// in this service's own Postgres, which is why the gateway routes the read here
// rather than to the read-service projection.
func (s *Server) handleDeliveryLog(writer http.ResponseWriter, request *http.Request) {
	userExternalID, authenticated := authenticatedUserID(request)
	if !authenticated {
		writeError(
			writer,
			request,
			http.StatusUnauthorized,
			"unauthorized",
			"Missing "+GatewayUserHeader+" header — request must traverse the API gateway.",
		)
		return
	}
	if s.deliveryLog == nil {
		writeError(writer, request, http.StatusServiceUnavailable, "service_unavailable", "Delivery log is unavailable.")
		return
	}

	query, queryErr := readDeliveryLogQuery(request, userExternalID)
	if queryErr != nil {
		writeValidationError(writer, request, queryErr)
		return
	}

	page, listErr := s.deliveryLog.List(request.Context(), query)
	if errors.Is(listErr, services.ErrWebhookNotFound) {
		writeError(writer, request, http.StatusNotFound, "not_found", "Webhook not found.")
		return
	}
	if listErr != nil {
		slog.Error("delivery log query failed", "webhook_id", query.WebhookID, "error", listErr)
		writeError(writer, request, http.StatusInternalServerError, "internal_error", "Could not read the delivery log.")
		return
	}

	rows, nextCursor, previousCursor := paginate(page.Rows, query)
	writeOK(writer, presentDeliveries(rows), map[string]any{
		"limit":       query.Limit,
		"total":       page.Total,
		"next_cursor": nextCursor,
		"prev_cursor": previousCursor,
	})
}

// validationError carries both halves of the error contract: code and detail
type validationError struct {
	field      string
	detailCode string
	message    string
	status     int
	errorCode  string
}

func (e validationError) Error() string {
	return e.message
}

func writeValidationError(writer http.ResponseWriter, request *http.Request, err error) {
	var failure validationError
	if !errors.As(err, &failure) {
		writeError(writer, request, http.StatusUnprocessableEntity, "validation_failed", err.Error())
		return
	}

	writeError(
		writer,
		request,
		failure.status,
		failure.errorCode,
		failure.message,
		errorDetail{
			Field:   failure.field,
			Code:    failure.detailCode,
			Message: failure.message,
		},
	)
}

func readDeliveryLogQuery(request *http.Request, userExternalID string) (types.DeliveryLogQuery, error) {
	parameters := request.URL.Query()

	filters := types.DeliveryLogFilters{
		Status: strings.TrimSpace(parameters.Get(statusParam)),
		Event:  strings.TrimSpace(parameters.Get(eventParam)),
	}
	if filters.Status != "" && !types.IsKnownDeliveryStatus(filters.Status) {
		return types.DeliveryLogQuery{}, validationError{
			field:      statusParam,
			detailCode: "invalid",
			message:    "Unknown delivery status. Legal values: " + strings.Join(statusNames(), ", ") + ".",
			status:     http.StatusUnprocessableEntity,
			errorCode:  "validation_failed",
		}
	}
	if filters.Event != "" && !types.IsKnownEvent(filters.Event) {
		return types.DeliveryLogQuery{}, validationError{
			field:      eventParam,
			detailCode: "unknown_event_type",
			message:    "Unknown event type. See GET /webhooks/event-types.",
			status:     http.StatusUnprocessableEntity,
			errorCode:  "validation_failed",
		}
	}

	limit, limitErr := readLimit(parameters.Get(limitParam))
	if limitErr != nil {
		return types.DeliveryLogQuery{}, limitErr
	}

	webhookID := request.PathValue("webhookID")
	anchor, anchorErr := readAnchor(parameters.Get(cursorParam), filters, webhookID)
	if anchorErr != nil {
		return types.DeliveryLogQuery{}, anchorErr
	}

	return types.DeliveryLogQuery{
		UserExternalID: userExternalID,
		WebhookID:      webhookID,
		Filters:        filters,
		Limit:          limit,
		Anchor:         anchor,
	}, nil
}

func readLimit(raw string) (int, error) {
	if strings.TrimSpace(raw) == "" {
		return defaultLimit, nil
	}

	parsed, parseErr := strconv.Atoi(strings.TrimSpace(raw))
	if parseErr != nil {
		return 0, validationError{
			field:      limitParam,
			detailCode: "invalid",
			message:    "limit must be an integer.",
			status:     http.StatusUnprocessableEntity,
			errorCode:  "validation_failed",
		}
	}

	if parsed < minimumLimit {
		return minimumLimit, nil
	}
	if parsed > maximumLimit {
		return maximumLimit, nil
	}

	return parsed, nil
}

func readAnchor(
	raw string,
	filters types.DeliveryLogFilters,
	webhookID string,
) (*types.DeliveryAnchor, error) {
	if strings.TrimSpace(raw) == "" {
		return nil, nil
	}

	anchor, decodeErr := decodeCursor(raw, queryFingerprint(filters, webhookID))
	if errors.Is(decodeErr, errCursorMismatch) {
		return nil, validationError{
			field:      cursorParam,
			detailCode: "invalid",
			message:    "This cursor belongs to a different query.",
			status:     http.StatusUnprocessableEntity,
			errorCode:  "cursor_mismatch",
		}
	}
	if decodeErr != nil {
		return nil, validationError{
			field:      cursorParam,
			detailCode: "invalid",
			message:    "This cursor cannot be read.",
			status:     http.StatusUnprocessableEntity,
			errorCode:  "cursor_invalid",
		}
	}

	return anchor, nil
}

// paginate trims the lookahead row and mints the cursors that navigate away
// from this page.
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

	fingerprint := queryFingerprint(query.Filters, query.WebhookID)
	backwards := query.Anchor != nil && query.Anchor.Backwards

	var nextCursor, previousCursor *string
	if !backwards && hasMore || backwards {
		last := rows[len(rows)-1]
		cursor := encodeCursor(directionNext, last.CreatedAt, last.ID, fingerprint)
		nextCursor = &cursor
	}
	if query.Anchor != nil && (!backwards || hasMore) {
		first := rows[0]
		cursor := encodeCursor(directionPrevious, first.CreatedAt, first.ID, fingerprint)
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
