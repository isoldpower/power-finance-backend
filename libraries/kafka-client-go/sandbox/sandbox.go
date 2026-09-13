package sandbox

import (
	"os"
	"strings"

	"github.com/power-finance/kafka-client-go/headers"
)

const (
	BaggageHeader         = "baggage"
	HTTPHeader            = "X-Sandbox"
	BaggageEntryName      = "sandbox-id"
	EnvironmentVariableID = "SANDBOX_ID"
	GroupIDSeparator      = "-sbx-"
)

func ResolveOwnID() string {
	return strings.TrimSpace(os.Getenv(EnvironmentVariableID))
}

func ScopeGroupID(groupID string, sandboxID string) string {
	if sandboxID == "" {
		return groupID
	}

	return groupID + GroupIDSeparator + sandboxID
}

func ReadIDFromHeaders(kafkaHeaders headers.KafkaHeaders) string {
	baggageHeaderValue, isFound := headers.Get(kafkaHeaders, BaggageHeader)
	if !isFound {
		return ""
	}

	return ReadBaggageEntry(baggageHeaderValue, BaggageEntryName)
}

func ReadBaggageEntry(baggageHeaderValue string, entryName string) string {
	for _, rawEntry := range strings.Split(baggageHeaderValue, ",") {
		entryName_, entryValue, hasSeparator := strings.Cut(rawEntry, "=")
		if !hasSeparator {
			continue
		}
		if strings.TrimSpace(entryName_) != entryName {
			continue
		}

		propertyFreeValue, _, _ := strings.Cut(entryValue, ";")

		return strings.TrimSpace(propertyFreeValue)
	}

	return ""
}
