package consumer

import (
	"context"
	"errors"
	"log/slog"
	"time"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/consumer/dedupe"
	"github.com/power-finance/kafka-client-go/publisher"
)

type UserHandler func(
	ctx context.Context,
	message kafkaclient.ConsumedMessage,
) error

const (
	inProcessBackoffPerAttempt = 100 * time.Millisecond
	inProcessBackoffCeiling    = 1 * time.Second
)

type MessageHandlerConfig struct {
	Policy         RetryPolicy
	RetryPublisher *publisher.RetryPublisher
	DLQPublisher   *publisher.DLQPublisher
	DedupeStore    dedupe.Store
	EventID        dedupe.EventIDExtractor
	Logger         *slog.Logger
}

type MessageHandler struct {
	userHandler    UserHandler
	retryPolicy    RetryPolicy
	dedupeGate     *dedupe.Gate
	terminalRouter *TerminalRouter
	sleep          func(ctx context.Context, duration time.Duration) error
}

func NewMessageHandler(userHandler UserHandler, config MessageHandlerConfig) *MessageHandler {
	return &MessageHandler{
		userHandler: userHandler,
		retryPolicy: config.Policy,
		dedupeGate: dedupe.NewGate(
			config.DedupeStore,
			config.EventID,
			config.Logger,
		),
		terminalRouter: NewTerminalRouter(
			config.Policy,
			config.RetryPublisher,
			config.DLQPublisher,
			config.Logger,
		),
		sleep: sleepUnlessCancelled,
	}
}

func (h *MessageHandler) Handle(ctx context.Context, message kafkaclient.ConsumedMessage) error {
	alreadyProcessed, dedupeErr := h.dedupeGate.AlreadyProcessed(ctx, message)
	if dedupeErr != nil {
		return dedupeErr
	} else if alreadyProcessed {
		return nil
	}

	retryContext := RetryContextFromMessage(message)
	lastRetryableError, runErr := h.runInProcessAttempts(ctx, message, retryContext)
	if runErr != nil {
		return runErr
	} else if lastRetryableError == nil {
		return nil
	}

	return h.terminalRouter.RouteTerminalFailure(
		ctx,
		message,
		lastRetryableError,
		retryContext,
		h.retryPolicy.MaxInProcessAttempts,
	)
}

func (h *MessageHandler) runInProcessAttempts(
	ctx context.Context,
	message kafkaclient.ConsumedMessage,
	retryContext RetryContext,
) (lastRetryableError error, terminalError error) {
	var lastRetryable error

	for attemptNumber := 1; attemptNumber <= h.retryPolicy.MaxInProcessAttempts; attemptNumber++ {
		handlerError := h.userHandler(ctx, message)
		if handlerError == nil {
			return nil, nil
		} else if isShutdownInProgress(ctx, handlerError) {
			return nil, handlerError
		}

		switch {
		case errors.Is(handlerError, kafkaclient.ErrPoison):
			routeError := h.terminalRouter.RouteImmediateFailure(
				ctx, message, handlerError, retryContext, attemptNumber, "poison",
			)
			return nil, routeError

		case h.retryPolicy.IsRetryable(handlerError):
			lastRetryable = handlerError
			isLastAttempt := attemptNumber == h.retryPolicy.MaxInProcessAttempts
			if !isLastAttempt {
				backoff := inProcessBackoffForAttempt(attemptNumber)
				if sleepError := h.sleep(ctx, backoff); sleepError != nil {
					return nil, sleepError
				}
			}

		default:
			routeError := h.terminalRouter.RouteImmediateFailure(
				ctx, message, handlerError, retryContext, attemptNumber, "non_retryable",
			)
			return nil, routeError
		}
	}

	return lastRetryable, nil
}

func isShutdownInProgress(ctx context.Context, handlerError error) bool {
	return ctx.Err() != nil || errors.Is(handlerError, context.Canceled)
}

func inProcessBackoffForAttempt(attemptNumber int) time.Duration {
	backoff := inProcessBackoffPerAttempt * time.Duration(attemptNumber)
	return min(backoff, inProcessBackoffCeiling)
}

func sleepUnlessCancelled(ctx context.Context, duration time.Duration) error {
	if duration <= 0 {
		return nil
	}

	timer := time.NewTimer(duration)
	defer timer.Stop()

	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}
