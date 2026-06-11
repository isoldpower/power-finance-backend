package acknowledgement

import (
	"testing"

	"github.com/twmb/franz-go/pkg/kgo"
)

func TestModesMapToFranzGoAcks(t *testing.T) {
	cases := map[string]struct {
		mode                AcknowledgementMode
		expectedAcks        kgo.Acks
		supportsIdempotence bool
		expectedName        string
	}{
		"all in-sync replicas": {
			mode:                AcknowledgeAllInSyncReplicas,
			expectedAcks:        kgo.AllISRAcks(),
			supportsIdempotence: true,
			expectedName:        "all-in-sync-replicas",
		},
		"leader only": {
			mode:                AcknowledgeLeaderOnly,
			expectedAcks:        kgo.LeaderAck(),
			supportsIdempotence: false,
			expectedName:        "leader-only",
		},
		"none": {
			mode:                AcknowledgeNone,
			expectedAcks:        kgo.NoAck(),
			supportsIdempotence: false,
			expectedName:        "none",
		},
	}

	for name, testCase := range cases {
		if got := testCase.mode.RequiredAcknowledgements(); got != testCase.expectedAcks {
			t.Fatalf("%s: expected acks %v, got %v", name, testCase.expectedAcks, got)
		}
		if got := testCase.mode.SupportsIdempotence(); got != testCase.supportsIdempotence {
			t.Fatalf("%s: expected idempotence support %v, got %v", name, testCase.supportsIdempotence, got)
		}
		if got := testCase.mode.Name(); got != testCase.expectedName {
			t.Fatalf("%s: expected name %q, got %q", name, testCase.expectedName, got)
		}
	}
}

func TestOnlyAllInSyncReplicasSupportsIdempotence(t *testing.T) {
	modes := []AcknowledgementMode{
		AcknowledgeAllInSyncReplicas,
		AcknowledgeLeaderOnly,
		AcknowledgeNone,
	}

	idempotenceCapable := 0
	for _, mode := range modes {
		if mode.SupportsIdempotence() {
			idempotenceCapable++
		}
	}

	if idempotenceCapable != 1 {
		t.Fatalf("expected exactly one idempotence-capable mode, got %d", idempotenceCapable)
	}
	if !AcknowledgeAllInSyncReplicas.SupportsIdempotence() {
		t.Fatal("expected all-in-sync-replicas to be the idempotence-capable mode")
	}
}
