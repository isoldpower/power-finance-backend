package acknowledgement

import "github.com/twmb/franz-go/pkg/kgo"

type leaderOnlyAcknowledgement struct {
}

func (leaderOnlyAcknowledgement) RequiredAcknowledgements() kgo.Acks {
	return kgo.LeaderAck()
}
func (leaderOnlyAcknowledgement) SupportsIdempotence() bool {
	return false
}
func (leaderOnlyAcknowledgement) Name() string {
	return "leader-only"
}
