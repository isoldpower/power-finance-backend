package config

import (
	"path/filepath"
	"testing"
	"time"
)

func TestLoadAppliesDefaultsWhenNoConfigFile(t *testing.T) {
	t.Setenv("WEBHOOK_SERVICE_CONFIG_FILE", filepath.Join(t.TempDir(), "absent.yaml"))

	cfg := Load()

	if cfg.Server.Port != 8002 {
		t.Errorf("default server port = %d, want 8002", cfg.Server.Port)
	}
	if cfg.Kafka.GroupID != "webhook-service.deliveries" {
		t.Errorf("default group id = %q", cfg.Kafka.GroupID)
	}
	if cfg.Delivery.MaxAttempts != 5 {
		t.Errorf("default max attempts = %d, want 5", cfg.Delivery.MaxAttempts)
	}
	if cfg.Delivery.Timeout != 10*time.Second {
		t.Errorf("default timeout = %v, want 10s", cfg.Delivery.Timeout)
	}
	if cfg.Delivery.SchedulerInterval != 15*time.Second {
		t.Errorf("default scheduler interval = %v, want 15s", cfg.Delivery.SchedulerInterval)
	}
}

func TestSplitTopicsTrimsAndDropsEmpty(t *testing.T) {
	topics := splitTopics(" events.async , , webhooks.retry ")

	if len(topics) != 2 || topics[0] != "events.async" || topics[1] != "webhooks.retry" {
		t.Fatalf("unexpected topics: %#v", topics)
	}
}

func TestSplitViperPathBreaksDownPath(t *testing.T) {
	dir, name, ext := SplitViperPath("/etc/webhook/config.yaml")

	if dir != "/etc/webhook" || name != "config" || ext != "yaml" {
		t.Fatalf("unexpected split: dir=%q name=%q ext=%q", dir, name, ext)
	}
}
