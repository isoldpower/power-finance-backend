package handlers

import (
	"bytes"

	"services/push-service/push_service/types"
)

func formatServerSentEvent(event types.OutboxEvent) []byte {
	var frame bytes.Buffer

	frame.WriteString("event: ")
	frame.WriteString(event.EventType)
	frame.WriteString("\n")

	if event.EventID != "" {
		frame.WriteString("id: ")
		frame.WriteString(event.EventID)
		frame.WriteString("\n")
	}

	for _, payloadLine := range bytes.Split(event.Payload, []byte("\n")) {
		frame.WriteString("data: ")
		frame.Write(payloadLine)
		frame.WriteString("\n")
	}

	frame.WriteString("\n")

	return frame.Bytes()
}
