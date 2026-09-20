package sandbox

// TrafficMatcher decides whether a message belongs to this process.
type TrafficMatcher struct {
	ownSandboxID string
}

func NewTrafficMatcher(ownSandboxID string) TrafficMatcher {
	return TrafficMatcher{ownSandboxID: ownSandboxID}
}

func NewTrafficMatcherFromEnvironment() TrafficMatcher {
	return NewTrafficMatcher(ResolveOwnID())
}

func (m TrafficMatcher) OwnSandboxID() string {
	return m.ownSandboxID
}

func (m TrafficMatcher) IsBaseline() bool {
	return m.ownSandboxID == ""
}

func (m TrafficMatcher) IsOwnedTraffic(messageSandboxID string) bool {
	return messageSandboxID == m.ownSandboxID
}
