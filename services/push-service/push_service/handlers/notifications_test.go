package handlers

import (
	"strings"
	"testing"
	"time"

	"services/push-service/push_service/types"
)

// fakeHeartbeat records its lifecycle without emitting frames, so SSE frame
// assertions stay deterministic.
type fakeHeartbeat struct {
	started chan struct{}
	stopped chan struct{}
}

func newFakeHeartbeat() *fakeHeartbeat {
	return &fakeHeartbeat{
		started: make(chan struct{}),
		stopped: make(chan struct{}),
	}
}

func (f *fakeHeartbeat) SpawnHeartbeatMessages(_ chan<- []byte) { close(f.started) }
func (f *fakeHeartbeat) StopTicker()                            { close(f.stopped) }

func newTestHandler(heartbeat types.Heartbeat) *SSENotificationsHandler {
	var poolUnusedBySpinUntilDone types.ClientsPool
	var projectionUnusedBySpinUntilDone types.EventsProjector

	return NewSSENotificationsHandler(
		poolUnusedBySpinUntilDone,
		projectionUnusedBySpinUntilDone,
		func() types.Heartbeat { return heartbeat },
	)
}

func assertClosed(t *testing.T, name string, channel <-chan struct{}) {
	t.Helper()
	select {
	case <-channel:
	default:
		t.Fatalf("expected %s to be closed", name)
	}
}

func TestSpinUntilDoneForwardsEventsAsFrames(t *testing.T) {
	heartbeat := newFakeHeartbeat()
	handler := newTestHandler(heartbeat)

	gone := make(chan struct{})
	events := make(chan types.OutboxEvent)
	responses := make(chan []byte, 1)

	done := make(chan struct{})
	go func() {
		handler.SpinUntilDone(gone, events, responses)
		close(done)
	}()

	events <- types.OutboxEvent{EventType: "WalletCreated", EventID: "evt-1", Payload: []byte(`{"a":1}`)}

	select {
	case frame := <-responses:
		got := string(frame)
		if !strings.Contains(got, "event: WalletCreated") ||
			!strings.Contains(got, "id: evt-1") ||
			!strings.Contains(got, `data: {"a":1}`) {
			t.Fatalf("unexpected SSE frame: %q", got)
		}
	case <-time.After(time.Second):
		t.Fatal("expected an SSE frame for the delivered event")
	}

	close(gone)

	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("expected SpinUntilDone to return when the client is gone")
	}

	assertClosed(t, "heartbeat start", heartbeat.started)
	assertClosed(t, "heartbeat stop", heartbeat.stopped)
}

func TestSpinUntilDoneReturnsWhenEventsChannelCloses(t *testing.T) {
	heartbeat := newFakeHeartbeat()
	handler := newTestHandler(heartbeat)

	done := make(chan struct{})
	events := make(chan types.OutboxEvent)
	go func() {
		handler.SpinUntilDone(make(chan struct{}), events, make(chan []byte, 1))
		close(done)
	}()

	close(events)

	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("expected SpinUntilDone to return when the events channel closes")
	}

	assertClosed(t, "heartbeat stop", heartbeat.stopped)
}
