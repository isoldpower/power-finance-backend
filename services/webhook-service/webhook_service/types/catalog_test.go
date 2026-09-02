package types

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

const catalogJSONPath = "../../../../libraries/webhook-catalog-py/webhook_catalog_py/catalog.json"

type catalogFile struct {
	EventTypes []WebhookEventType `json:"event_types"`
}

// TestCatalogMatchesSharedFile is the drift guard: the Go publisher and the
// Python API must agree on the catalog, and a row added to only one of them
// would otherwise produce a subscription that never fires.
func TestCatalogMatchesSharedFile(t *testing.T) {
	raw, readErr := os.ReadFile(filepath.Clean(catalogJSONPath))
	if readErr != nil {
		t.Fatalf("read shared catalog: %v", readErr)
	}

	var shared catalogFile
	if unmarshalErr := json.Unmarshal(raw, &shared); unmarshalErr != nil {
		t.Fatalf("decode shared catalog: %v", unmarshalErr)
	}

	if !reflect.DeepEqual(shared.EventTypes, EventCatalog) {
		t.Fatalf("catalog drift:\nshared: %+v\ngo:     %+v", shared.EventTypes, EventCatalog)
	}
}

func TestWebhookEventTypeForMapsMetadataUpdates(t *testing.T) {
	if got := WebhookEventTypeFor("TransactionMetadataUpdated"); got != "transaction.updated" {
		t.Fatalf("expected transaction.updated, got %q", got)
	}
}

func TestWebhookEventTypeForIgnoresUnpublishedEvents(t *testing.T) {
	if got := WebhookEventTypeFor("WalletDeleted"); got != "" {
		t.Fatalf("expected no webhook event, got %q", got)
	}
}
