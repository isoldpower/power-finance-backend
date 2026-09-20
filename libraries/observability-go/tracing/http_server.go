package tracing

import (
	"net/http"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

func WrapHTTPHandler(handler http.Handler, serverName string) http.Handler {
	return otelhttp.NewHandler(
		handler,
		serverName,
	)
}
