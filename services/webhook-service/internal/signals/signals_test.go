package signals

import (
	"context"
	"errors"
	"syscall"
	"testing"
	"time"
)

func TestNotifyContextLiveUntilSignal(t *testing.T) {
	ctx, stop := NotifyContext()
	defer stop()

	if ctx.Err() != nil {
		t.Fatalf("context should be live before any signal, got %v", ctx.Err())
	}
}

func TestNotifyContextCancelsOnSignal(t *testing.T) {
	ctx, stop := NotifyContext()
	defer stop()

	if signalErr := syscall.Kill(syscall.Getpid(), syscall.SIGTERM); signalErr != nil {
		t.Fatalf("failed to send SIGTERM: %v", signalErr)
	}

	select {
	case <-ctx.Done():
		if !errors.Is(ctx.Err(), context.Canceled) {
			t.Fatalf("context error = %v, want context.Canceled", ctx.Err())
		}
	case <-time.After(2 * time.Second):
		t.Fatal("context was not cancelled after SIGTERM")
	}
}
