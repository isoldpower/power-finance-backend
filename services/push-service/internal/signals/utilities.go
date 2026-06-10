package signals

import "services/push-service/internal/log"

func TrackSignalSafe[T interface{}](signal SignalHandler, stopChannel <-chan T) {
	signalContext, cancel := signal.GetContext()
	defer cancel()

	select {
	case <-stopChannel:
		log.Debugln("Signal interrupted by stop channel")

		return
	case <-signalContext.Done():
		log.Debugln("Signal context done received")

		shutdownHandler := signal.GetOnShutdown()
		handlerErr := shutdownHandler(signalContext)
		if handlerErr != nil {
			log.Debugln("shutdown handler error", handlerErr)
		}
	}
}
