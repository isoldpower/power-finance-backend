package logging

import (
	"log/slog"
	"testing"
)

func TestLevelFromName(t *testing.T) {
	cases := map[string]slog.Level{
		"debug":   slog.LevelDebug,
		"warn":    slog.LevelWarn,
		"error":   slog.LevelError,
		"ERROR":   slog.LevelError,
		"":        slog.LevelInfo,
		"unknown": slog.LevelInfo,
	}

	for value, want := range cases {
		if got := levelFromName(value); got != want {
			t.Errorf("levelFromName(%q) = %v, want %v", value, got, want)
		}
	}
}

func TestSetupTakesTheLevelFromTheEnvironment(t *testing.T) {
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

func TestSetLevelReinstallsTheDefaultLogger(t *testing.T) {
	SetLevel("debug")
	if !slog.Default().Enabled(t.Context(), slog.LevelDebug) {
		t.Error("debug should be enabled after SetLevel(debug)")
	}

	SetLevel("warn")
	if slog.Default().Enabled(t.Context(), slog.LevelInfo) {
		t.Error("info should be suppressed after SetLevel(warn)")
	}
}
