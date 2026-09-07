package services

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"strconv"
	"time"

	"services/webhook-service/webhook_service/types"
)

const (
	signatureHeader = "X-Webhook-Signature"
	eventTypeHeader = "X-Webhook-Event"
	deliveryHeader  = "X-Webhook-Delivery"
	timestampHeader = "X-Webhook-Timestamp"

	dialTimeout = 10 * time.Second
)

var errRedirectsBlocked = errors.New("sender: redirects are not allowed")

type senderOptions struct {
	allowPrivateAddresses bool
}

// SenderOption customises an HTTPSender.
type SenderOption func(*senderOptions)

// WithAllowPrivateAddresses disables the SSRF address guard.
func WithAllowPrivateAddresses() SenderOption {
	return func(options *senderOptions) {
		options.allowPrivateAddresses = true
	}
}

// HTTPSender POSTs signed payloads to customer endpoints.
type HTTPSender struct {
	client *http.Client
}

// NewHTTPSender builds a sender with an SSRF address guard enabled by default.
func NewHTTPSender(timeout time.Duration, opts ...SenderOption) *HTTPSender {
	var options senderOptions
	for _, opt := range opts {
		opt(&options)
	}

	dialer := &net.Dialer{Timeout: dialTimeout}
	if !options.allowPrivateAddresses {
		dialer.Control = guardDialAddress
	}

	transport := &http.Transport{
		DialContext:           dialer.DialContext,
		ForceAttemptHTTP2:     true,
		MaxIdleConns:          100,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: time.Second,
	}

	return &HTTPSender{
		client: &http.Client{
			Timeout:   timeout,
			Transport: transport,
			CheckRedirect: func(_ *http.Request, _ []*http.Request) error {
				return errRedirectsBlocked
			},
		},
	}
}

// Send signs the payload and POSTs it, erroring on transport failure or a non-2xx.
func (s *HTTPSender) Send(
	ctx context.Context,
	delivery types.Delivery,
	secret string,
	at time.Time,
) error {
	if schemeErr := validateTargetScheme(delivery.TargetURL); schemeErr != nil {
		return schemeErr
	}

	request, requestErr := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		delivery.TargetURL,
		bytes.NewReader(delivery.Payload),
	)
	if requestErr != nil {
		return fmt.Errorf("sender: build request: %w", requestErr)
	}

	timestamp := strconv.FormatInt(at.Unix(), 10)
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set(timestampHeader, timestamp)
	request.Header.Set(signatureHeader, signPayload(secret, timestamp, delivery.Payload))
	request.Header.Set(eventTypeHeader, delivery.EventType)
	request.Header.Set(deliveryHeader, delivery.EventID)

	response, sendErr := s.client.Do(request)
	if sendErr != nil {
		return fmt.Errorf("sender: post: %w", sendErr)
	}
	defer func() {
		_, _ = io.Copy(io.Discard, response.Body)
		_ = response.Body.Close()
	}()

	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return fmt.Errorf("sender: non-2xx response: %d", response.StatusCode)
	}

	return nil
}
