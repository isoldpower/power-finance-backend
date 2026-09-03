package contract

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
	CursorVersion     = 1
	FingerprintLength = 16
	OrderSignature    = "created_at:desc,id:desc"
	IsoLayout         = "2006-01-02T15:04:05.999999-07:00"

	DirectionNext     = "next"
	DirectionPrevious = "prev"
)

var (
	ErrCursorInvalid  = errors.New("cursor_invalid")
	ErrCursorMismatch = errors.New("cursor_mismatch")
)

type cursorPayload struct {
	Version     int      `json:"v"`
	Direction   string   `json:"d"`
	Values      []string `json:"k"`
	Fingerprint string   `json:"f"`
}

// QueryFingerprint binds a cursor to the query that produced it, so a client
// cannot carry a cursor from one filter set into another and silently skip rows.
func QueryFingerprint(filters types.DeliveryLogFilters, webhookID string) string {
	material := map[string]any{
		"order": OrderSignature,
		"query": map[string]any{
			"webhook_id": webhookID,
			"status":     nullable(filters.Status),
			"event":      nullable(filters.Event),
		},
	}

	canonical, _ := json.Marshal(material)
	digest := sha256.Sum256(canonical)

	return hex.EncodeToString(digest[:])[:FingerprintLength]
}

func nullable(value string) any {
	if value == "" {
		return nil
	}

	return value
}

func EncodeCursor(direction string, createdAt time.Time, id string, fingerprint string) string {
	payload, _ := json.Marshal(cursorPayload{
		Version:     CursorVersion,
		Direction:   direction,
		Values:      []string{createdAt.Format(IsoLayout), id},
		Fingerprint: fingerprint,
	})

	return strings.TrimRight(
		base64.URLEncoding.EncodeToString(payload),
		"=",
	)
}

func DecodeCursor(raw string, fingerprint string) (*types.DeliveryAnchor, error) {
	padded := raw + strings.Repeat("=", (4-len(raw)%4)%4)
	decoded, decodeErr := base64.URLEncoding.DecodeString(padded)
	if decodeErr != nil {
		return nil, ErrCursorInvalid
	}

	var payload cursorPayload
	if unmarshalErr := json.Unmarshal(decoded, &payload); unmarshalErr != nil {
		return nil, ErrCursorInvalid
	}
	if payload.Version != CursorVersion || len(payload.Values) != 2 {
		return nil, ErrCursorInvalid
	}
	if payload.Direction != DirectionNext && payload.Direction != DirectionPrevious {
		return nil, ErrCursorInvalid
	}
	if payload.Fingerprint != fingerprint {
		return nil, ErrCursorMismatch
	}

	createdAt, parseErr := parseCursorTime(payload.Values[0])
	if parseErr != nil {
		return nil, ErrCursorInvalid
	}

	return &types.DeliveryAnchor{
		CreatedAt: createdAt,
		ID:        payload.Values[1],
		Backwards: payload.Direction == DirectionPrevious,
	}, nil
}

func parseCursorTime(raw string) (time.Time, error) {
	parsed, parseErr := time.Parse(
		time.RFC3339Nano,
		strings.Replace(raw, "+00:00", "Z", 1),
	)
	if parseErr != nil {
		return time.Time{}, fmt.Errorf("cursor: parse timestamp: %w", parseErr)
	}

	return parsed, nil
}
