package signals

import (
	"context"
	"log/slog"
	"os/signal"
	"syscall"
)

type KeyboardSignalHandler struct {
	handler SignalHandlerFunc
}

func NewKeyboardSignalHandler(handler SignalHandlerFunc) *KeyboardSignalHandler {
	return &KeyboardSignalHandler{
		handler: handler,
	}
}

func (ksh *KeyboardSignalHandler) GetContext() (context.Context, context.CancelFunc) {
	return signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
}

func (ksh *KeyboardSignalHandler) GetOnShutdown() SignalHandlerFunc {
	return func(ctx context.Context) error {
		slog.Debug("shutdown signal received, handling action")

		return ksh.handler(ctx)
	}
}
