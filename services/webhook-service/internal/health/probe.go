package health

import "sync/atomic"

type Probe struct {
	ready atomic.Bool
}

func NewProbe() *Probe {
	return &Probe{}
}

// MarkReady marks the probe as being ready to accept connections.
func (p *Probe) MarkReady() {
	p.ready.Store(true)
}

// MarkUnready marks the probe as being busy and not ready to accept connections.
func (p *Probe) MarkUnready() {
	p.ready.Store(false)
}

// IsReady returns current readiness state of the probe.
func (p *Probe) IsReady() bool {
	return p.ready.Load()
}
