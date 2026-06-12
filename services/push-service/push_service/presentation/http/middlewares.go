package http

import (
	"fmt"
	"net/http"
	"strings"

	"services/push-service/push_service/handlers"
)

const gatewayAuthMiddlewarePriority = 0

func GatewayAuthMiddleware(
	writer http.ResponseWriter,
	request *http.Request,
) (*http.Request, bool) {
	if request.Method == http.MethodOptions {
		return request, true
	}

	externalUserID := strings.TrimSpace(request.Header.Get(handlers.GatewayUserHeader))
	if externalUserID == "" {
		rejectionMessage := fmt.Sprintf(
			"Missing %s header — request must traverse the API gateway",
			handlers.GatewayUserHeader,
		)
		http.Error(writer, rejectionMessage, http.StatusUnauthorized)

		return request, false
	}

	authenticatedContext := handlers.WithAuthenticatedUserID(request.Context(), externalUserID)

	return request.WithContext(authenticatedContext), true
}
