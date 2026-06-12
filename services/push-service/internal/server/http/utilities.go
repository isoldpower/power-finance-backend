package http

import (
	"net"
	"slices"
)

func createListener(address string, network HTTPNetworkType) (net.Listener, error) {
	listener, listenerErr := net.Listen(string(network), address)
	if listenerErr != nil {
		return listener, listenerErr
	}

	return listener, nil
}

func sortMiddlewares(middlewares []*RouteMiddleware) []*RouteMiddleware {
	slices.SortStableFunc(middlewares, func(first *RouteMiddleware, second *RouteMiddleware) int {
		return first.priority - second.priority
	})

	return middlewares
}
