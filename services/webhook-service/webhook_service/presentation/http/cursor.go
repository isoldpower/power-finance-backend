package http

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"services/webhook-service/webhook_service/types"
)

const (
	cursorVersion     = 1
	fingerprintLength = 16
	orderSignature    = "created_at:desc,id:desc"
	isoLayout         = "2006-01-02T15:04:05.999999-07:00"

	directionNext     = "next"
	directionPrevious = "prev"
)

var (
	errCursorInvalid  = errors.New("cursor_invalid")
	errCursorMismatch = errors.New("cursor_mismatch")
)

type cursorPayload struct {
	Version     int      `json:"v"`
	Direction   string   `json:"d"`
	Values      []string `json:"k"`
	Fingerprint string   `json:"f"`
}

// queryFingerprint binds a cursor to the query that produced it, so a client
// cannot carry a cursor from one filter set into another and silently skip rows.
func queryFingerprint(filters types.DeliveryLogFilters, webhookID string) string {
	material := map[string]any{
		"order": orderSignature,
		"query": map[string]any{
			"webhook_id": webhookID,
			"status":     nullable(filters.Status),
			"event":      nullable(filters.Event),
		},
	}

	canonical, _ := json.Marshal(material)
	digest := sha256.Sum256(canonical)

	return hex.EncodeToString(digest[:])[:fingerprintLength]
}

func nullable(value string) any {
	if value == "" {
		return nil
	}

	return value
}

func encodeCursor(direction string, createdAt time.Time, id string, fingerprint string) string {
	payload, _ := json.Marshal(cursorPayload{
		Version:     cursorVersion,
		Direction:   direction,
		Values:      []string{createdAt.Format(isoLayout), id},
		Fingerprint: fingerprint,
	})

	return strings.TrimRight(
		base64.URLEncoding.EncodeToString(payload),
		"=",
	)
}

func decodeCursor(raw string, fingerprint string) (*types.DeliveryAnchor, error) {
	padded := raw + strings.Repeat("=", (4-len(raw)%4)%4)
	decoded, decodeErr := base64.URLEncoding.DecodeString(padded)
	if decodeErr != nil {
		return nil, errCursorInvalid
	}

	var payload cursorPayload
	if unmarshalErr := json.Unmarshal(decoded, &payload); unmarshalErr != nil {
		return nil, errCursorInvalid
	}
	if payload.Version != cursorVersion || len(payload.Values) != 2 {
		return nil, errCursorInvalid
	}
	if payload.Direction != directionNext && payload.Direction != directionPrevious {
		return nil, errCursorInvalid
	}
	if payload.Fingerprint != fingerprint {
		return nil, errCursorMismatch
	}

	createdAt, parseErr := parseCursorTime(payload.Values[0])
	if parseErr != nil {
		return nil, errCursorInvalid
	}

	return &types.DeliveryAnchor{
		CreatedAt: createdAt,
		ID:        payload.Values[1],
		Backwards: payload.Direction == directionPrevious,
	}, nil
}

func parseCursorTime(raw string) (time.Time, error) {
	parsed, parseErr := time.Parse(time.RFC3339Nano, strings.Replace(raw, "+00:00", "Z", 1))
	if parseErr != nil {
		return time.Time{}, fmt.Errorf("cursor: parse timestamp: %w", parseErr)
	}

	return parsed, nil
}
