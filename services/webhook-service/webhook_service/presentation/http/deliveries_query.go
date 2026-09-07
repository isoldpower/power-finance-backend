package http

import (
	"errors"
	"net/http"
	"services/webhook-service/webhook_service/presentation/http/contract"
	"strconv"
	"strings"

	"services/webhook-service/webhook_service/types"
)

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

	anchor, decodeErr := contract.DecodeCursor(
		raw,
		contract.QueryFingerprint(filters, webhookID),
	)
	if errors.Is(decodeErr, contract.ErrCursorMismatch) {
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
