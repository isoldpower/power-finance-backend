package demotraces

import "regexp"

var demoSessionIdentifierPattern = regexp.MustCompile(`^[A-Za-z0-9_-]{16,64}$`)

func IsValidDemoSessionIdentifier(candidateIdentifier string) bool {
	return demoSessionIdentifierPattern.MatchString(candidateIdentifier)
}
