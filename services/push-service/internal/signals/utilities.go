package signals

import "log/slog"

func TrackSignalSafe[T any](signal SignalHandler, stopChannel <-chan T) {
	signalContext, cancel := signal.GetContext()
	defer cancel()

	select {
	case <-stopChannel:
		slog.Debug("signal tracking interrupted by stop channel")

		return
	case <-signalContext.Done():
		slog.Debug("shutdown signal context done")

		shutdownHandler := signal.GetOnShutdown()
		if handlerErr := shutdownHandler(signalContext); handlerErr != nil {
			slog.Error("shutdown handler failed", "error", handlerErr)
		}
	}
}
