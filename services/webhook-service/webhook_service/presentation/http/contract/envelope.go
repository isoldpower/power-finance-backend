package contract

import (
	"encoding/json"
	"net/http"
	"time"
)

// Envelope is the success shape every endpoint answers in.
type Envelope struct {
	Data  any            `json:"data,omitempty"`
	Error *ErrorBody     `json:"error,omitempty"`
	Meta  map[string]any `json:"meta"`
}

// ErrorBody is the error shape every endpoint fails in.
type ErrorBody struct {
	Code    string        `json:"code"`
	Message string        `json:"message"`
	Details []ErrorDetail `json:"details,omitempty"`
}

// ErrorDetail names one field a failure refused.
type ErrorDetail struct {
	Field   string `json:"field"`
	Code    string `json:"code"`
	Message string `json:"message"`
}

const correlationHeader = "X-Correlation-ID"

// WriteOK writes a 200 in the success envelope.
func WriteOK(writer http.ResponseWriter, data any, meta map[string]any) {
	if meta == nil {
		meta = map[string]any{}
	}

	writeJSON(writer, http.StatusOK, Envelope{Data: data, Meta: meta})
}

// WriteError writes a failure in the error envelope, correlation id included.
func WriteError(
	writer http.ResponseWriter,
	request *http.Request,
	status int,
	code string,
	message string,
	details ...ErrorDetail,
) {
	writeJSON(writer, status, Envelope{
		Error: &ErrorBody{Code: code, Message: message, Details: details},
		Meta: map[string]any{
			"request_id": request.Header.Get(correlationHeader),
			"timestamp":  time.Now().UTC().Format(IsoLayout),
		},
	})
}

func writeJSON(writer http.ResponseWriter, status int, body Envelope) {
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(status)

	if encodeErr := json.NewEncoder(writer).Encode(body); encodeErr != nil {
		logResponseEncodeFailed(encodeErr)
	}
}
