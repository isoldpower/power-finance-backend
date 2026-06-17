package consumer

import (
	"context"
	"log/slog"
	"time"

	kafkaclient "github.com/power-finance/kafka-client-go"
	"github.com/power-finance/kafka-client-go/publisher"
)

type TerminalRouter struct {
	retryPolicy    RetryPolicy
	retryPublisher *publisher.RetryPublisher
	dlqPublisher   *publisher.DLQPublisher
	logger         *slog.Logger
}

func NewTerminalRouter(
	retryPolicy RetryPolicy,
	retryPublisher *publisher.RetryPublisher,
	dlqPublisher *publisher.DLQPublisher,
	logger *slog.Logger,
) *TerminalRouter {
	if logger == nil {
		logger = slog.Default()
	}

	return &TerminalRouter{
		retryPolicy:    retryPolicy,
		retryPublisher: retryPublisher,
		dlqPublisher:   dlqPublisher,
		logger:         logger,
	}
}

func (r *TerminalRouter) RouteImmediateFailure(
	ctx context.Context,
	message kafkaclient.ConsumedMessage,
	cause error,
	retryContext RetryContext,
	inProcessAttemptsMade int,
	reason string,
) error {
	totalAttempts := retryContext.RetryTopicAttemptsConsumed + inProcessAttemptsMade
	publishErr := r.dlqPublisher.Publish(ctx, message, publisher.DLQPublication{
		Error:         cause,
		TotalAttempts: totalAttempts,
		FirstFailedAt: retryContext.FirstFailedAtOrNow(),
	})
	if publishErr != nil {
		return publishErr
	}

	r.logger.WarnContext(ctx, "kafka.handler."+reason,
		slog.String("topic", message.Topic),
		slog.String("error_class", kafkaclient.ErrorClass(cause)),
		slog.String("error", cause.Error()),
	)

	return nil
}

func (r *TerminalRouter) RouteTerminalFailure(
	ctx context.Context,
	message kafkaclient.ConsumedMessage,
	lastError error,
	retryContext RetryContext,
	inProcessAttemptsMade int,
) error {
	if r.retryTopicBudgetRemaining(retryContext) {
		return r.scheduleRetryTopicAttempt(ctx, message, lastError, retryContext)
	}

	return r.publishExhaustedToDLQ(ctx, message, lastError, retryContext, inProcessAttemptsMade)
}

func (r *TerminalRouter) retryTopicBudgetRemaining(retryContext RetryContext) bool {
	return retryContext.RetryTopicAttemptsConsumed < r.retryPolicy.MaxRetryTopicAttempts
}

func (r *TerminalRouter) scheduleRetryTopicAttempt(
	ctx context.Context,
	message kafkaclient.ConsumedMessage,
	lastError error,
	retryContext RetryContext,
) error {
	nextRetryTopicAttempt := retryContext.RetryTopicAttemptsConsumed + 1
	nextRetryAt := r.retryPolicy.ComputeRetryAt(nextRetryTopicAttempt, time.Time{})

	publishErr := r.retryPublisher.Publish(ctx, message, publisher.RetryPublication{
		Error:         lastError,
		NextRetryAt:   nextRetryAt,
		Attempt:       nextRetryTopicAttempt,
		FirstFailedAt: retryContext.FirstFailedAtOrNow(),
	})
	if publishErr != nil {
		return publishErr
	}

	r.logger.InfoContext(ctx, "kafka.handler.retry_scheduled",
		slog.String("topic", message.Topic),
		slog.Time("retry_at", nextRetryAt),
		slog.Int("retry_topic_attempt", nextRetryTopicAttempt),
		slog.String("error_class", kafkaclient.ErrorClass(lastError)),
		slog.String("error", lastError.Error()),
	)
	return nil
}

func (r *TerminalRouter) publishExhaustedToDLQ(
	ctx context.Context,
	message kafkaclient.ConsumedMessage,
	lastError error,
	retryContext RetryContext,
	inProcessAttemptsMade int,
) error {
	totalAttempts := retryContext.RetryTopicAttemptsConsumed + inProcessAttemptsMade
	publishErr := r.dlqPublisher.Publish(ctx, message, publisher.DLQPublication{
		Error:         lastError,
		TotalAttempts: totalAttempts,
		FirstFailedAt: retryContext.FirstFailedAtOrNow(),
	})
	if publishErr != nil {
		return publishErr
	}

	r.logger.WarnContext(ctx, "kafka.handler.exhausted",
		slog.String("topic", message.Topic),
		slog.Int("total_attempts", totalAttempts),
		slog.String("error_class", kafkaclient.ErrorClass(lastError)),
		slog.String("error", lastError.Error()),
	)
	return nil
}
