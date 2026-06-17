package logging

import (
	"log/slog"
	"os"
	"strings"
)

// Setup installs a JSON stdout slog logger as the default for early bootstrap;
// level from the LOG_LEVEL environment variable.
func Setup() {
	install(levelFromName(os.Getenv("LOG_LEVEL")))
}

// SetLevel reinstalls the default logger at the given level, used once the
// configuration (file + env) has been resolved.
func SetLevel(name string) {
	install(levelFromName(name))
}

func install(level slog.Level) {
	handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: level,
	})
	slog.SetDefault(slog.New(handler))
}

func levelFromName(name string) slog.Level {
	switch strings.ToLower(name) {
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
