package http

import (
	"context"
	"net/http"
)

const GatewayUserHeader = "X-User-Id"

type authenticatedUserContextKey struct{}

func WithAuthenticatedUserID(parent context.Context, externalUserID string) context.Context {
	return context.WithValue(parent, authenticatedUserContextKey{}, externalUserID)
}

func AuthenticatedUserID(request *http.Request) (string, bool) {
	externalUserID, present := request.Context().Value(authenticatedUserContextKey{}).(string)

	return externalUserID, present && externalUserID != ""
}
