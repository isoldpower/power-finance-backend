package topology

import (
	"encoding/json"
	"testing"
)

type topologyGroup struct {
	ID string `json:"id"`
}

type topologyNode struct {
	ID          string          `json:"id"`
	Name        string          `json:"name"`
	Type        string          `json:"type"`
	Group       string          `json:"group"`
	Deployment  string          `json:"deployment"`
	Description string          `json:"description"`
	Telemetry   json.RawMessage `json:"telemetry"`
}

type topologyConnection struct {
	From string `json:"from"`
	To   string `json:"to"`
	Kind string `json:"kind"`
}

type topologyDocument struct {
	Version     int                  `json:"version"`
	Groups      []topologyGroup      `json:"groups"`
	Nodes       []topologyNode       `json:"nodes"`
	Connections []topologyConnection `json:"connections"`
}

var knownNodeTypes = map[string]struct{}{
	"client": {}, "gateway": {}, "service": {}, "worker": {}, "stream-processor": {},
	"database": {}, "cache": {}, "ledger": {}, "search": {}, "topic": {},
	"connector": {}, "observability": {}, "external": {},
}

var knownConnectionKinds = map[string]struct{}{
	"request": {}, "query": {}, "publish": {}, "consume": {}, "cdc": {}, "push": {}, "telemetry": {},
}

func decodeTopologyDocument(t *testing.T) topologyDocument {
	t.Helper()

	var decodedDocument topologyDocument
	if decodeErr := json.Unmarshal(InfrastructureTopologyDocument(), &decodedDocument); decodeErr != nil {
		t.Fatalf("topology document is not valid JSON: %v", decodeErr)
	}

	return decodedDocument
}

func TestTopologyNodesAreUniqueAndComplete(t *testing.T) {
	decodedDocument := decodeTopologyDocument(t)

	knownGroups := make(map[string]struct{})
	for _, group := range decodedDocument.Groups {
		knownGroups[group.ID] = struct{}{}
	}

	seenNodeIdentifiers := make(map[string]struct{})
	for _, node := range decodedDocument.Nodes {
		if _, isDuplicate := seenNodeIdentifiers[node.ID]; isDuplicate {
			t.Fatalf("duplicate node id %q", node.ID)
		}
		seenNodeIdentifiers[node.ID] = struct{}{}

		if node.Name == "" || node.Description == "" || node.Deployment == "" {
			t.Fatalf("node %q is missing a name, description or deployment", node.ID)
		}
		if _, isKnownType := knownNodeTypes[node.Type]; !isKnownType {
			t.Fatalf("node %q has unknown type %q", node.ID, node.Type)
		}
		if _, isKnownGroup := knownGroups[node.Group]; !isKnownGroup {
			t.Fatalf("node %q references unknown group %q", node.ID, node.Group)
		}
	}
}

func TestTopologyConnectionsReferenceExistingNodes(t *testing.T) {
	decodedDocument := decodeTopologyDocument(t)

	nodeIdentifiers := make(map[string]struct{})
	for _, node := range decodedDocument.Nodes {
		nodeIdentifiers[node.ID] = struct{}{}
	}

	connectedNodeIdentifiers := make(map[string]struct{})
	for _, connection := range decodedDocument.Connections {
		for _, endpointIdentifier := range []string{connection.From, connection.To} {
			if _, exists := nodeIdentifiers[endpointIdentifier]; !exists {
				t.Fatalf("connection %s -> %s references unknown node %q", connection.From, connection.To, endpointIdentifier)
			}
			connectedNodeIdentifiers[endpointIdentifier] = struct{}{}
		}
		if _, isKnownKind := knownConnectionKinds[connection.Kind]; !isKnownKind {
			t.Fatalf("connection %s -> %s has unknown kind %q", connection.From, connection.To, connection.Kind)
		}
	}

	for nodeIdentifier := range nodeIdentifiers {
		if _, isConnected := connectedNodeIdentifiers[nodeIdentifier]; !isConnected {
			t.Fatalf("node %q has no connections", nodeIdentifier)
		}
	}
}
