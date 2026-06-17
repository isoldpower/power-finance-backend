package publisher

import (
	"strings"
	"testing"

	"github.com/power-finance/kafka-client-go/publisher/acknowledgement"
)

func TestDefaultProducerConfigBuildsOptions(t *testing.T) {
	options, err := buildClientOptions(DefaultProducerConfig("localhost:9092"))

	if err != nil {
		t.Fatal(err)
	}
	if len(options) == 0 {
		t.Fatal("expected client options to be built")
	}
}

func TestZeroValueConfigDefaultsToAllInSyncReplicasWithoutCompression(t *testing.T) {
	config := ProducerConfig{
		BootstrapServers:  "localhost:9092",
		EnableIdempotence: true,
	}

	if _, err := buildClientOptions(config); err != nil {
		t.Fatal(err)
	}
}

func TestIdempotenceRejectsLeaderOnlyAcknowledgement(t *testing.T) {
	config := DefaultProducerConfig("localhost:9092")
	config.Acknowledgement = acknowledgement.AcknowledgeLeaderOnly

	_, err := buildClientOptions(config)

	if err == nil {
		t.Fatal("expected idempotence + leader-only acknowledgement to be rejected")
	}
	if !strings.Contains(err.Error(), "leader-only") {
		t.Fatalf("expected error to name the acknowledgement mode, got %q", err)
	}
}

func TestIdempotenceRejectsNoAcknowledgement(t *testing.T) {
	config := DefaultProducerConfig("localhost:9092")
	config.Acknowledgement = acknowledgement.AcknowledgeNone

	if _, err := buildClientOptions(config); err == nil {
		t.Fatal("expected idempotence + no acknowledgement to be rejected")
	}
}

func TestWeakerAcknowledgementAllowedWithoutIdempotence(t *testing.T) {
	config := DefaultProducerConfig("localhost:9092")
	config.EnableIdempotence = false
	config.Acknowledgement = acknowledgement.AcknowledgeLeaderOnly

	if _, err := buildClientOptions(config); err != nil {
		t.Fatal(err)
	}
}

func TestClientIDOptionAddedOnlyWhenConfigured(t *testing.T) {
	withoutClientID, err := buildClientOptions(DefaultProducerConfig("localhost:9092"))
	if err != nil {
		t.Fatal(err)
	}

	config := DefaultProducerConfig("localhost:9092")
	config.ClientID = "write-service"
	withClientID, err := buildClientOptions(config)
	if err != nil {
		t.Fatal(err)
	}

	if len(withClientID) != len(withoutClientID)+1 {
		t.Fatalf(
			"expected exactly one extra option for client id, got %d vs %d",
			len(withClientID), len(withoutClientID),
		)
	}
}
