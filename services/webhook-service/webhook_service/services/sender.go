package services

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/http"
	"time"

	"services/webhook-service/webhook_service/types"
)

const (
	signatureHeader = "X-Webhook-Signature"
	eventTypeHeader = "X-Webhook-Event"
	deliveryHeader  = "X-Webhook-Delivery"
)

type HTTPSender struct {
	client *http.Client
}

func NewHTTPSender(timeout time.Duration) *HTTPSender {
	return &HTTPSender{
		client: &http.Client{Timeout: timeout},
	}
}

// Send signs the payload with the endpoint secret and POSTs it, returning an
// error on transport failure or a non-2xx response.
func (s *HTTPSender) Send(ctx context.Context, delivery types.Delivery, secret string) error {
	request, requestErr := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		delivery.TargetURL,
		bytes.NewReader(delivery.Payload),
	)
	if requestErr != nil {
		return fmt.Errorf("sender: build request: %w", requestErr)
	}

	request.Header.Set("Content-Type", "application/json")
	request.Header.Set(signatureHeader, signPayload(secret, delivery.Payload))
	request.Header.Set(eventTypeHeader, delivery.EventType)
	request.Header.Set(deliveryHeader, delivery.ID)

	response, sendErr := s.client.Do(request)
	if sendErr != nil {
		return fmt.Errorf("sender: post: %w", sendErr)
	}
	defer response.Body.Close()

	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return fmt.Errorf("sender: non-2xx response: %d", response.StatusCode)
	}

	return nil
}

func signPayload(secret string, payload []byte) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(payload)

	return "v1=" + hex.EncodeToString(mac.Sum(nil))
}
