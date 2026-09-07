package http

import (
	"context"
	"errors"
	"net/http"
	"services/webhook-service/webhook_service/presentation/http/contract"

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

func (s *Server) handleDeliveryLog(writer http.ResponseWriter, request *http.Request) {
	userExternalID, authenticated := authenticatedUserID(request)
	if !authenticated {
		contract.WriteError(
			writer,
			request,
			http.StatusUnauthorized,
			"unauthorized",
			"Missing "+GatewayUserHeader+" header — request must traverse the API gateway.",
		)
		return
	}

	if s.deliveryLog == nil {
		contract.WriteError(
			writer,
			request,
			http.StatusServiceUnavailable,
			"service_unavailable",
			"Delivery log is unavailable.",
		)
		return
	}

	query, queryErr := readDeliveryLogQuery(request, userExternalID)
	if queryErr != nil {
		writeValidationError(writer, request, queryErr)
		return
	}

	page, listErr := s.deliveryLog.List(request.Context(), query)
	if errors.Is(listErr, services.ErrWebhookNotFound) {
		contract.WriteError(
			writer,
			request,
			http.StatusNotFound,
			"not_found",
			"Webhook not found.",
		)

		return
	}
	if listErr != nil {
		logDeliveryLogQueryFailed(query.WebhookID, listErr)
		contract.WriteError(
			writer,
			request,
			http.StatusInternalServerError,
			"internal_error",
			"Could not read the delivery log.",
		)

		return
	}

	rows, nextCursor, previousCursor := paginate(page.Rows, query)
	contract.WriteOK(writer, presentDeliveries(rows), map[string]any{
		"limit":       query.Limit,
		"total":       page.Total,
		"next_cursor": nextCursor,
		"prev_cursor": previousCursor,
	})
}

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
		contract.WriteError(
			writer,
			request,
			http.StatusUnprocessableEntity,
			"validation_failed",
			err.Error(),
		)
		return
	}

	contract.WriteError(
		writer,
		request,
		failure.status,
		failure.errorCode,
		failure.message,
		contract.ErrorDetail{
			Field:   failure.field,
			Code:    failure.detailCode,
			Message: failure.message,
		},
	)
}
