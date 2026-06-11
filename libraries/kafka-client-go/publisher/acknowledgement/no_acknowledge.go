package acknowledgement

import "github.com/twmb/franz-go/pkg/kgo"

type noAcknowledgement struct {
}

func (noAcknowledgement) RequiredAcknowledgements() kgo.Acks {
	return kgo.NoAck()
}
func (noAcknowledgement) SupportsIdempotence() bool {
	return false
}
func (noAcknowledgement) Name() string {
	return "none"
}
