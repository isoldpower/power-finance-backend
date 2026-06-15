package logging

import (
	"log/slog"
	"testing"
)

func TestLevelFromEnvironment(t *testing.T) {
	cases := map[string]slog.Level{
		"debug":   slog.LevelDebug,
		"warn":    slog.LevelWarn,
		"error":   slog.LevelError,
		"ERROR":   slog.LevelError,
		"":        slog.LevelInfo,
		"unknown": slog.LevelInfo,
	}

	for value, want := range cases {
		t.Setenv("LOG_LEVEL", value)
		if got := levelFromEnvironment(); got != want {
			t.Errorf("levelFromEnvironment() with LOG_LEVEL=%q = %v, want %v", value, got, want)
		}
	}
}

func TestSetupInstallsLevelledDefaultLogger(t *testing.T) {
	t.Setenv("LOG_LEVEL", "error")

	Setup()

	logger := slog.Default()
	if logger.Enabled(t.Context(), slog.LevelInfo) {
		t.Error("info should be suppressed when LOG_LEVEL=error")
	}
	if !logger.Enabled(t.Context(), slog.LevelError) {
		t.Error("error should be enabled when LOG_LEVEL=error")
	}
}
