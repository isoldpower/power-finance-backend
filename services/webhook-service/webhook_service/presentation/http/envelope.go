package http

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"time"
)

// The response envelope every service in this API shares: a success carries
// `data` + `meta`, a failure carries `error` + `meta`.
type envelope struct {
	Data  any            `json:"data,omitempty"`
	Error *errorBody     `json:"error,omitempty"`
	Meta  map[string]any `json:"meta"`
}

type errorBody struct {
	Code    string        `json:"code"`
	Message string        `json:"message"`
	Details []errorDetail `json:"details,omitempty"`
}

type errorDetail struct {
	Field   string `json:"field"`
	Code    string `json:"code"`
	Message string `json:"message"`
}

const correlationHeader = "X-Correlation-ID"

func writeOK(writer http.ResponseWriter, data any, meta map[string]any) {
	if meta == nil {
		meta = map[string]any{}
	}

	writeJSON(writer, http.StatusOK, envelope{Data: data, Meta: meta})
}

func writeError(
	writer http.ResponseWriter,
	request *http.Request,
	status int,
	code string,
	message string,
	details ...errorDetail,
) {
	writeJSON(writer, status, envelope{
		Error: &errorBody{Code: code, Message: message, Details: details},
		Meta: map[string]any{
			"request_id": request.Header.Get(correlationHeader),
			"timestamp":  time.Now().UTC().Format(isoLayout),
		},
	})
}

func writeJSON(writer http.ResponseWriter, status int, body envelope) {
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(status)

	if encodeErr := json.NewEncoder(writer).Encode(body); encodeErr != nil {
		slog.Error("failed to encode response", "error", encodeErr)
	}
}
