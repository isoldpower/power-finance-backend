package acknowledgement

import "github.com/twmb/franz-go/pkg/kgo"

type AcknowledgementMode interface {
	RequiredAcknowledgements() kgo.Acks
	SupportsIdempotence() bool
	Name() string
}

var (
	AcknowledgeAllInSyncReplicas AcknowledgementMode = allInSyncReplicasAcknowledgement{}
	AcknowledgeLeaderOnly        AcknowledgementMode = leaderOnlyAcknowledgement{}
	AcknowledgeNone              AcknowledgementMode = noAcknowledgement{}
)
