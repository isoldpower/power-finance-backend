package signals

import "context"

type SignalHandlerFunc func(ctx context.Context) error

type SignalHandler interface {
	GetContext() (context.Context, context.CancelFunc)
	GetOnShutdown() SignalHandlerFunc
}
