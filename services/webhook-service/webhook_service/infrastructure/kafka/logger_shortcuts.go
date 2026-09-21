package kafka

import "log/slog"

func logConsumerStarted() {
	slog.Info("kafka consumer started")
}

func logConsumerStopped() {
	slog.Info("kafka consumer stopped")
}

func logHandlerFailed(err error) {
	slog.Error("kafka handler failed, leaving offset uncommitted", "error", err)
}

func logCommitFailed(topic string, partition int32, offset int64, err error) {
	slog.Error(
		"kafka commit failed",
		"topic", topic,
		"partition", partition,
		"offset", offset,
		"error", err,
	)
}

func logFetchFailed(topic string, partition int32, err error) {
	slog.Error("kafka fetch error", "topic", topic, "partition", partition, "error", err)
}

func logForeignSandboxMessageSkipped(messageSandboxID string, ownSandboxID string) {
	slog.Debug(
		"kafka message belongs to another sandbox, skipping",
		"messageSandbox", messageSandboxID,
		"ownSandbox", ownSandboxID,
	)
}
