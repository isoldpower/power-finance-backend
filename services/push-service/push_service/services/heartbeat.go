package services

import "time"

type HeartbeatService struct {
	interval    time.Duration
	doneChannel chan struct{}
}

func NewHeartbeatService(interval time.Duration) *HeartbeatService {
	return &HeartbeatService{
		interval:    interval,
		doneChannel: make(chan struct{}),
	}
}

// SpawnHeartbeatMessages routine that spawns heartbeat messages each 'interval' period.
// Useful as some browsers prohibit never-closing channels and it will help connection alive.
func (hs *HeartbeatService) SpawnHeartbeatMessages(receiver chan<- []byte) {
	ticker := time.NewTicker(hs.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			receiver <- []byte(": heartbeat\n\n")
		case <-hs.doneChannel:
			return
		}
	}
}

// StopTicker stops spawning heartbeat messages.
func (hs *HeartbeatService) StopTicker() {
	hs.doneChannel <- struct{}{}
}
