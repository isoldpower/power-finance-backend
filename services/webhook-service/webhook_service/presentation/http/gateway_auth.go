package http

import (
	"net/http"
	"strings"
)

// GatewayUserHeader carries the Clerk subject the gateway verified.
const GatewayUserHeader = "X-User-Id"

func authenticatedUserID(request *http.Request) (string, bool) {
	externalUserID := strings.TrimSpace(request.Header.Get(GatewayUserHeader))

	return externalUserID, externalUserID != ""
}
