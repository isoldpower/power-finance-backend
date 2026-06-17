package signals

import (
	"context"
	"os/signal"
	"syscall"
)

// NotifyContext returns a context cancelled on SIGINT/SIGTERM, driving
// graceful shutdown of the consumer loop and HTTP server.
func NotifyContext() (context.Context, context.CancelFunc) {
	return signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
}
