package services

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"syscall"
	"time"

	"services/webhook-service/webhook_service/types"
)

const (
	signatureHeader = "X-Webhook-Signature"
	eventTypeHeader = "X-Webhook-Event"
	deliveryHeader  = "X-Webhook-Delivery"

	dialTimeout = 10 * time.Second
)

var errRedirectsBlocked = errors.New("sender: redirects are not allowed")

type senderOptions struct {
	allowPrivateAddresses bool
}

// SenderOption customises an HTTPSender.
type SenderOption func(*senderOptions)

// WithAllowPrivateAddresses disables the SSRF address guard. It exists for tests
// that target loopback httptest servers and must not be used in production.
func WithAllowPrivateAddresses() SenderOption {
	return func(options *senderOptions) {
		options.allowPrivateAddresses = true
	}
}

type HTTPSender struct {
	client *http.Client
}

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

// Send signs the payload with the endpoint secret and POSTs it, returning an
// error on transport failure or a non-2xx response.
func (s *HTTPSender) Send(ctx context.Context, delivery types.Delivery, secret string) error {
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

	request.Header.Set("Content-Type", "application/json")
	request.Header.Set(signatureHeader, signPayload(secret, delivery.Payload))
	request.Header.Set(eventTypeHeader, delivery.EventType)
	request.Header.Set(deliveryHeader, delivery.ID)

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

func validateTargetScheme(targetURL string) error {
	parsed, parseErr := url.Parse(targetURL)
	if parseErr != nil {
		return fmt.Errorf("sender: parse target url: %w", parseErr)
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return fmt.Errorf("sender: unsupported target scheme %q", parsed.Scheme)
	}

	return nil
}

// guardDialAddress rejects connections to loopback, private, link-local and
// unspecified addresses. It runs on every dial (including redirects, which are
// blocked anyway) against the already-resolved IP, so it also defeats
// DNS-rebinding to an internal target.
func guardDialAddress(_ string, address string, _ syscall.RawConn) error {
	host, _, splitErr := net.SplitHostPort(address)
	if splitErr != nil {
		return fmt.Errorf("sender: parse dial address: %w", splitErr)
	}

	ip := net.ParseIP(host)
	if ip == nil {
		return fmt.Errorf("sender: unresolved dial address %q", host)
	}
	if isBlockedAddress(ip) {
		return fmt.Errorf("sender: blocked target address %s", ip)
	}

	return nil
}

func isBlockedAddress(ip net.IP) bool {
	return ip.IsLoopback() ||
		ip.IsPrivate() ||
		ip.IsLinkLocalUnicast() ||
		ip.IsLinkLocalMulticast() ||
		ip.IsInterfaceLocalMulticast() ||
		ip.IsUnspecified()
}

func signPayload(secret string, payload []byte) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(payload)

	return "v1=" + hex.EncodeToString(mac.Sum(nil))
}
