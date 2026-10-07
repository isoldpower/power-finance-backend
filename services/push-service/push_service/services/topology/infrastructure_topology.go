package topology

import _ "embed"

//go:embed infrastructure_topology.json
var infrastructureTopologyDocument []byte

func InfrastructureTopologyDocument() []byte {
	return infrastructureTopologyDocument
}
