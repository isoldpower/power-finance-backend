package http

import (
	"fmt"
	"net/http"
	"strings"

	"services/push-service/internal/correlation"
)

const (
	correlationMiddlewarePriority = -10
	gatewayAuthMiddlewarePriority = 0
)

// CorrelationIDMiddleware propagates X-Correlation-ID into context and response, generating a fallback id when absent.
func CorrelationIDMiddleware(
	writer http.ResponseWriter,
	request *http.Request,
) (*http.Request, bool) {
	correlationID := strings.TrimSpace(request.Header.Get(correlation.Header))
	if correlationID == "" {
		correlationID = correlation.NewID()
	}

	writer.Header().Set(correlation.Header, correlationID)
	correlatedContext := correlation.WithID(request.Context(), correlationID)

	return request.WithContext(correlatedContext), true
}

func GatewayAuthMiddleware(
	writer http.ResponseWriter,
	request *http.Request,
) (*http.Request, bool) {
	if request.Method == http.MethodOptions {
		return request, true
	}

	externalUserID := strings.TrimSpace(request.Header.Get(GatewayUserHeader))
	if externalUserID == "" {
		rejectionMessage := fmt.Sprintf(
			"Missing %s header — request must traverse the API gateway",
			GatewayUserHeader,
		)
		http.Error(writer, rejectionMessage, http.StatusUnauthorized)

		return request, false
	}

	authenticatedContext := WithAuthenticatedUserID(request.Context(), externalUserID)

	return request.WithContext(authenticatedContext), true
}
