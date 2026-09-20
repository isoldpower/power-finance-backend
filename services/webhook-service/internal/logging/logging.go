package logging

import (
	"log/slog"
	"os"
	"strings"

	"github.com/power-finance/observability-go/logging"
)

// Setup installs a JSON stdout slog logger as the default; level from LOG_LEVEL.
//
// Wrapped in the shared trace-context handler so every line carries trace_id,
// span_id and sandbox_id, the way the Python services' formatter does.
func Setup() {
	handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: levelFromEnvironment(),
	})
	slog.SetDefault(slog.New(logging.NewTraceContextHandler(handler)))
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
