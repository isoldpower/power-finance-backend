package logging

import (
	"log/slog"
	"os"
	"strings"
)

// Setup installs a JSON stdout slog logger as the default; level from LOG_LEVEL.
func Setup() {
	handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: levelFromEnvironment(),
	})
	slog.SetDefault(slog.New(handler))
}

func levelFromEnvironment() slog.Level {
	switch strings.ToLower(os.Getenv("LOG_LEVEL")) {
	case "debug":
		return slog.LevelDebug
	case "warn":
		return slog.LevelWarn
	case "error":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}
