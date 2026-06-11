package acknowledgement

import "github.com/twmb/franz-go/pkg/kgo"

type allInSyncReplicasAcknowledgement struct {
}

func (allInSyncReplicasAcknowledgement) RequiredAcknowledgements() kgo.Acks {
	return kgo.AllISRAcks()
}
func (allInSyncReplicasAcknowledgement) SupportsIdempotence() bool {
	return true
}
func (allInSyncReplicasAcknowledgement) Name() string {
	return "all-in-sync-replicas"
}
