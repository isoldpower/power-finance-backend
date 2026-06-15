package health

import (
	"sync"
	"testing"
)

func TestProbeStartsUnready(t *testing.T) {
	if NewProbe().IsReady() {
		t.Fatal("a fresh probe should not be ready")
	}
}

func TestProbeMarkReadyAndUnready(t *testing.T) {
	probe := NewProbe()

	probe.MarkReady()
	if !probe.IsReady() {
		t.Fatal("probe should be ready after MarkReady")
	}

	probe.MarkUnready()
	if probe.IsReady() {
		t.Fatal("probe should be unready after MarkUnready")
	}
}

func TestProbeConcurrentAccessIsRaceFree(t *testing.T) {
	probe := NewProbe()

	var waitGroup sync.WaitGroup
	for range 100 {
		waitGroup.Add(2)
		go func() {
			defer waitGroup.Done()
			probe.MarkReady()
		}()
		go func() {
			defer waitGroup.Done()
			_ = probe.IsReady()
		}()
	}
	waitGroup.Wait()

	if !probe.IsReady() {
		t.Fatal("probe should be ready after all writers marked it ready")
	}
}
