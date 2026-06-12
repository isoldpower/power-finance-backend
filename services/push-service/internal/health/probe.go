package health

import "sync/atomic"

// Probe is a readiness flag flipped by the consumer loop and read by /readyz.
type Probe struct {
	ready atomic.Bool
}

func NewProbe() *Probe {
	return &Probe{}
}

func (p *Probe) MarkReady() {
	p.ready.Store(true)
}

func (p *Probe) MarkUnready() {
	p.ready.Store(false)
}

func (p *Probe) IsReady() bool {
	return p.ready.Load()
}
