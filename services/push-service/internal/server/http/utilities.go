package http

import (
	"net"
)

func createListener(address string, network HTTPNetworkType) (net.Listener, error) {
	listener, listenerErr := net.Listen(string(network), address)
	if listenerErr != nil {
		return listener, listenerErr
	}

	return listener, nil
}
