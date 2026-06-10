package utilities

import "context"

func ChannelToContext[T any](parentContext context.Context, channel <-chan T) (context.Context, context.CancelFunc) {
	currentContext, cancel := context.WithCancel(parentContext)

	go func() {
		select {
		case <-channel:
			cancel()
			return
		case <-currentContext.Done():
			return
		}
	}()

	return currentContext, cancel
}
