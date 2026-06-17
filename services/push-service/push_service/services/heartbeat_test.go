package services

import (
	"testing"
	"time"
)

func TestHeartbeatEmitsFramesOnInterval(t *testing.T) {
	heartbeat := NewHeartbeatService(5 * time.Millisecond)
	receiver := make(chan []byte, 1)

	go heartbeat.SpawnHeartbeatMessages(receiver)
	defer heartbeat.StopTicker()

	select {
	case frame := <-receiver:
		if string(frame) != ": heartbeat\n\n" {
			t.Fatalf("unexpected heartbeat frame: %q", frame)
		}
	case <-time.After(time.Second):
		t.Fatal("expected a heartbeat frame within the interval")
	}
}

func TestHeartbeatStopTickerHaltsBlockedEmission(t *testing.T) {
	heartbeat := NewHeartbeatService(time.Millisecond)
	unbufferedNeverDrainedReceiver := make(chan []byte)

	stopped := make(chan struct{})
	go func() {
		heartbeat.SpawnHeartbeatMessages(unbufferedNeverDrainedReceiver)
		close(stopped)
	}()

	const longEnoughForTickerToFireAndBlockOnSend = 10 * time.Millisecond
	time.Sleep(longEnoughForTickerToFireAndBlockOnSend)
	heartbeat.StopTicker()

	select {
	case <-stopped:
	case <-time.After(time.Second):
		t.Fatal("expected heartbeat goroutine to stop even while blocked on send")
	}
}
