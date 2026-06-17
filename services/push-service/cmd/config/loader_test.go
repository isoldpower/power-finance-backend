package config

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func clearConfigEnvironment(t *testing.T) {
	t.Helper()

	variables := []string{
		"PUSH_SERVICE_CONFIG_FILE",
		"PUSH_SERVICE_HOST",
		"PUSH_SERVICE_PORT",
		"PUSH_SERVICE_HEARTBEAT_INTERVAL_SECONDS",
		"KAFKA_BOOTSTRAP_SERVERS",
		"KAFKA_OUTBOX_TOPIC",
		"LOG_LEVEL",
	}
	for _, variable := range variables {
		t.Setenv(variable, "")
		os.Unsetenv(variable)
	}
}

func writeConfigFile(t *testing.T, content string) string {
	t.Helper()

	path := filepath.Join(t.TempDir(), "config.yaml")
	if writeErr := os.WriteFile(path, []byte(content), 0o644); writeErr != nil {
		t.Fatal(writeErr)
	}

	return path
}

func TestLoadDefaults(t *testing.T) {
	clearConfigEnvironment(t)

	loadedConfig := Load()

	if loadedConfig.Server.Host != "localhost" || loadedConfig.Server.Port != 8001 {
		t.Fatalf("expected default server config, got %+v", loadedConfig.Server)
	}
	if loadedConfig.Server.HeartbeatInterval != 15*time.Second {
		t.Fatalf("expected default 15s heartbeat, got %v", loadedConfig.Server.HeartbeatInterval)
	}
	if loadedConfig.Kafka.BootstrapServers != "localhost:9092" {
		t.Fatalf("expected default bootstrap servers, got %q", loadedConfig.Kafka.BootstrapServers)
	}
	if len(loadedConfig.Kafka.OutboxTopics) != 1 || loadedConfig.Kafka.OutboxTopics[0] != "events.async" {
		t.Fatalf("expected default topic events.async, got %v", loadedConfig.Kafka.OutboxTopics)
	}
}

func TestLoadReadsEnvironmentOverrides(t *testing.T) {
	clearConfigEnvironment(t)
	t.Setenv("PUSH_SERVICE_HOST", "0.0.0.0")
	t.Setenv("PUSH_SERVICE_PORT", "9001")
	t.Setenv("PUSH_SERVICE_HEARTBEAT_INTERVAL_SECONDS", "25")
	t.Setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
	t.Setenv("KAFKA_OUTBOX_TOPIC", "events.async, events.audit")

	loadedConfig := Load()

	if loadedConfig.Server.Host != "0.0.0.0" || loadedConfig.Server.Port != 9001 {
		t.Fatalf("expected overridden server config, got %+v", loadedConfig.Server)
	}
	if loadedConfig.Server.HeartbeatInterval != 25*time.Second {
		t.Fatalf("expected 25s heartbeat, got %v", loadedConfig.Server.HeartbeatInterval)
	}
	if loadedConfig.Kafka.BootstrapServers != "kafka:9092" {
		t.Fatalf("expected kafka:9092, got %q", loadedConfig.Kafka.BootstrapServers)
	}
	topics := loadedConfig.Kafka.OutboxTopics
	if len(topics) != 2 || topics[0] != "events.async" || topics[1] != "events.audit" {
		t.Fatalf("expected two trimmed topics, got %v", topics)
	}
}

func TestLoadReadsYamlConfigFile(t *testing.T) {
	clearConfigEnvironment(t)

	configPath := writeConfigFile(t, `
push_service:
  host: 0.0.0.0
  port: 9100
  heartbeat_interval_seconds: 20

kafka:
  bootstrap_servers: kafka:9092
`)
	t.Setenv("PUSH_SERVICE_CONFIG_FILE", configPath)

	loadedConfig := Load()

	if loadedConfig.Server.Host != "0.0.0.0" || loadedConfig.Server.Port != 9100 {
		t.Fatalf("expected server config from yaml, got %+v", loadedConfig.Server)
	}
	if loadedConfig.Server.HeartbeatInterval != 20*time.Second {
		t.Fatalf("expected 20s heartbeat from yaml, got %v", loadedConfig.Server.HeartbeatInterval)
	}
	if loadedConfig.Kafka.BootstrapServers != "kafka:9092" {
		t.Fatalf("expected bootstrap servers from yaml, got %q", loadedConfig.Kafka.BootstrapServers)
	}
	if len(loadedConfig.Kafka.OutboxTopics) != 1 || loadedConfig.Kafka.OutboxTopics[0] != "events.async" {
		t.Fatalf("expected defaults to fill yaml gaps, got %v", loadedConfig.Kafka.OutboxTopics)
	}
}

func TestEnvironmentWinsOverYamlConfigFile(t *testing.T) {
	clearConfigEnvironment(t)

	configPath := writeConfigFile(t, "push_service:\n  port: 9100\n")
	t.Setenv("PUSH_SERVICE_CONFIG_FILE", configPath)
	t.Setenv("PUSH_SERVICE_PORT", "9200")

	loadedConfig := Load()

	if loadedConfig.Server.Port != 9200 {
		t.Fatalf("expected environment to win over yaml, got %d", loadedConfig.Server.Port)
	}
}

func TestLoadToleratesMissingConfigFile(t *testing.T) {
	clearConfigEnvironment(t)
	t.Setenv("PUSH_SERVICE_CONFIG_FILE", filepath.Join(t.TempDir(), "absent.yaml"))

	loadedConfig := Load()

	if loadedConfig.Server.Port != 8001 {
		t.Fatalf("expected defaults with missing config file, got %d", loadedConfig.Server.Port)
	}
}

func TestSplitViperPath(t *testing.T) {
	configDir, configName, configType := SplitViperPath("./configs/push.yaml")

	if configDir != "configs" || configName != "push" || configType != "yaml" {
		t.Fatalf("unexpected split: %q %q %q", configDir, configName, configType)
	}
}

func TestSplitTopicsDropsEmptyEntries(t *testing.T) {
	topics := splitTopics("events.async,, ,events.audit,")

	if len(topics) != 2 {
		t.Fatalf("expected 2 topics, got %v", topics)
	}
}
