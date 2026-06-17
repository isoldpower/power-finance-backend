package http

import "net/http"

type HttpServerRoute struct {
	Pattern string
	Handler http.HandlerFunc
}
