package topology

import (
	"encoding/json"
	"fmt"
)

type ServiceNameSet map[string]struct{}

func (serviceNames ServiceNameSet) Contains(serviceName string) bool {
	_, isKnown := serviceNames[serviceName]
	return isKnown
}

type serviceNamesDocument struct {
	Nodes []struct {
		Telemetry *struct {
			ServiceNames []string `json:"serviceNames"`
		} `json:"telemetry"`
	} `json:"nodes"`
}

func KnownServiceNames() (ServiceNameSet, error) {
	return parseKnownServiceNames(InfrastructureTopologyDocument())
}

func parseKnownServiceNames(topologyDocument []byte) (ServiceNameSet, error) {
	var decodedDocument serviceNamesDocument
	if decodeErr := json.Unmarshal(topologyDocument, &decodedDocument); decodeErr != nil {
		return nil, fmt.Errorf("topology: decode service names: %w", decodeErr)
	}

	knownServiceNames := make(ServiceNameSet)
	for _, node := range decodedDocument.Nodes {
		if node.Telemetry == nil {
			continue
		}
		for _, serviceName := range node.Telemetry.ServiceNames {
			knownServiceNames[serviceName] = struct{}{}
		}
	}
	if len(knownServiceNames) == 0 {
		return nil, fmt.Errorf("topology: document declares no service names")
	}

	return knownServiceNames, nil
}
