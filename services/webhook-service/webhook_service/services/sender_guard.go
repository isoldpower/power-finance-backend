package services

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net"
	"net/url"
	"syscall"
)

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

func signPayload(secret string, timestamp string, payload []byte) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(timestamp))
	mac.Write([]byte("."))
	mac.Write(payload)

	return "v1=" + hex.EncodeToString(mac.Sum(nil))
}
