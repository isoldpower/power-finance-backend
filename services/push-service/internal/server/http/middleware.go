package http

import "net/http"

type RouteMiddlewareFunc func(http.ResponseWriter, *http.Request) (*http.Request, bool)

type RouteMiddleware struct {
	handler  RouteMiddlewareFunc
	priority int
}

func NewRouteMiddleware(
	handler RouteMiddlewareFunc,
	priority int,
) *RouteMiddleware {
	return &RouteMiddleware{
		handler:  handler,
		priority: priority,
	}
}

func (rm *RouteMiddleware) ServeHTTP(
	writer http.ResponseWriter,
	request *http.Request,
) (*http.Request, bool) {
	return rm.handler(writer, request)
}
