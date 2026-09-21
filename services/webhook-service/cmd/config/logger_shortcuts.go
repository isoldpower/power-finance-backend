package config

import "log/slog"

func logConfigFileUnreadable(path string, err error) {
	slog.Warn("failed to read config file", "path", path, "error", err)
}
