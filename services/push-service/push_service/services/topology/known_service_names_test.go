package topology

import "testing"

func TestKnownServiceNamesCoverEveryTracedProcess(t *testing.T) {
	knownServiceNames, parseErr := KnownServiceNames()
	if parseErr != nil {
		t.Fatal(parseErr)
	}

	for _, tracedServiceName := range []string{
		"api-gateway",
		"write-service",
		"write-automation-engine",
		"read-write-consumer",
		"ai-dispatcher",
		"push-service",
		"webhook-service",
		"antifraud-jobmanager",
		"antifraud-taskmanager",
	} {
		if !knownServiceNames.Contains(tracedServiceName) {
			t.Fatalf("expected %q to be a known service", tracedServiceName)
		}
	}
}

func TestNodesWithoutTelemetryContributeNoServiceNames(t *testing.T) {
	knownServiceNames, _ := KnownServiceNames()

	for _, untracedNodeIdentifier := range []string{"debezium", "immudb", "postgres-write", "clerk", "unknown"} {
		if knownServiceNames.Contains(untracedNodeIdentifier) {
			t.Fatalf("expected %q not to be a known service", untracedNodeIdentifier)
		}
	}
}

func TestDocumentWithoutServiceNamesIsRejected(t *testing.T) {
	if _, parseErr := parseKnownServiceNames([]byte(`{"nodes":[{"telemetry":null}]}`)); parseErr == nil {
		t.Fatal("expected a document without service names to be rejected")
	}
	if _, parseErr := parseKnownServiceNames([]byte(`not json`)); parseErr == nil {
		t.Fatal("expected malformed JSON to be rejected")
	}
}
