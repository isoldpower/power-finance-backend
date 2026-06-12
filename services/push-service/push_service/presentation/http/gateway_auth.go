package http

import (
	"context"
	"net/http"
)

const GatewayUserHeader = "X-User-Id"

type authenticatedUserContextKey struct{}

// WithAuthenticatedUserID returns a context which stores authentication results
// derived directly from Gateway authentication.
func WithAuthenticatedUserID(parent context.Context, externalUserID string) context.Context {
	return context.WithValue(
		parent,
		authenticatedUserContextKey{},
		externalUserID,
	)
}

// AuthenticatedUserID retrieves the authentication state from the context
// populated by WithAuthenticatedUserID function.
func AuthenticatedUserID(request *http.Request) (string, bool) {
	externalUserID, present := request.
		Context().
		Value(authenticatedUserContextKey{}).(string)

	return externalUserID, present && externalUserID != ""
}
