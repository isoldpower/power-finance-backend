package contract

import "log/slog"

func logResponseEncodeFailed(err error) {
	slog.Error("failed to encode response", "error", err)
}
