package cli

import "log/slog"

func logCLIExecutionFailed(err error) {
	slog.Error("cli execution failed", "error", err)
}
