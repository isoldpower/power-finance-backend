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

type attemptOutcome int

const (
	outcomeProcessed attemptOutcome = iota
	outcomeRoutedToDLQ
	outcomeRetryableExhausted
)

type MessageHandler struct {
	userHandler    UserHandler
	retryPolicy    RetryPolicy
	dedupeGate     *dedupe.Gate
	terminalRouter *TerminalRouter
	logger         *slog.Logger
	sleep          func(ctx context.Context, duration time.Duration) error
}

func NewMessageHandler(userHandler UserHandler, config MessageHandlerConfig) *MessageHandler {
	logger := config.Logger
	if logger == nil {
		logger = slog.Default()
	}

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
		logger: logger,
		sleep:  sleepUnlessCancelled,
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
	outcome, lastRetryableError, runErr := h.runInProcessAttempts(ctx, message, retryContext)
	if runErr != nil {
		return runErr
	}

	switch outcome {
	case outcomeProcessed:
		return h.markProcessedBestEffort(ctx, message)
	case outcomeRoutedToDLQ:
		return nil
	case outcomeRetryableExhausted:
		return h.terminalRouter.RouteTerminalFailure(
			ctx,
			message,
			lastRetryableError,
			retryContext,
			h.retryPolicy.MaxInProcessAttempts,
		)
	}

	return nil
}

// markProcessedBestEffort records a handled event for dedupe; a mark failure is
// logged not returned, since the handler succeeded and redelivery would reprocess it.
func (h *MessageHandler) markProcessedBestEffort(ctx context.Context, message kafkaclient.ConsumedMessage) error {
	if markErr := h.dedupeGate.MarkProcessed(ctx, message); markErr != nil {
		h.logger.WarnContext(ctx, "kafka.dedupe.mark_failed", slog.String("error", markErr.Error()))
	}

	return nil
}

func (h *MessageHandler) runInProcessAttempts(
	ctx context.Context,
	message kafkaclient.ConsumedMessage,
	retryContext RetryContext,
) (outcome attemptOutcome, lastRetryableError error, terminalError error) {
	var lastRetryable error

	for attemptNumber := 1; attemptNumber <= h.retryPolicy.MaxInProcessAttempts; attemptNumber++ {
		handlerError := h.userHandler(ctx, message)
		if handlerError == nil {
			return outcomeProcessed, nil, nil
		} else if isShutdownInProgress(ctx, handlerError) {
			return outcomeRoutedToDLQ, nil, handlerError
		}

		switch {
		case errors.Is(handlerError, kafkaclient.ErrPoison):
			routeError := h.terminalRouter.RouteImmediateFailure(
				ctx, message, handlerError, retryContext, attemptNumber, "poison",
			)
			return outcomeRoutedToDLQ, nil, routeError

		case h.retryPolicy.IsRetryable(handlerError):
			lastRetryable = handlerError
			isLastAttempt := attemptNumber == h.retryPolicy.MaxInProcessAttempts
			if !isLastAttempt {
				backoff := inProcessBackoffForAttempt(attemptNumber)
				if sleepError := h.sleep(ctx, backoff); sleepError != nil {
					return outcomeRoutedToDLQ, nil, sleepError
				}
			}

		default:
			routeError := h.terminalRouter.RouteImmediateFailure(
				ctx, message, handlerError, retryContext, attemptNumber, "non_retryable",
			)
			return outcomeRoutedToDLQ, nil, routeError
		}
	}

	return outcomeRetryableExhausted, lastRetryable, nil
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
