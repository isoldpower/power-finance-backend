package signals

import (
	"context"
	"os/signal"
	"services/push-service/internal/log"
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
		log.Debugln("Context interrupted by keyboard input. Handling action...")

		return ksh.handler(ctx)
	}
}
