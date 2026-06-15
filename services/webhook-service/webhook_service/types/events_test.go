package types

import "testing"

func TestWebhookEventTypeForKnownEvents(t *testing.T) {
	cases := map[string]string{
		"TransactionCreated": "transaction.created",
		"TransactionUpdated": "transaction.updated",
		"TransactionDeleted": "transaction.deleted",
	}

	for outboxType, expected := range cases {
		if got := WebhookEventTypeFor(outboxType); got != expected {
			t.Errorf("WebhookEventTypeFor(%q) = %q, want %q", outboxType, got, expected)
		}
	}
}

func TestWebhookEventTypeForUnknownEventIsBlank(t *testing.T) {
	if got := WebhookEventTypeFor("WalletCreated"); got != "" {
		t.Errorf("expected blank for non-deliverable event, got %q", got)
	}
}
