package publisher

import (
	"fmt"
	"unicode/utf8"
)

const (
	errorMessageMaxBytes = 1024
	errorStackMaxBytes   = 8192
)

func errorDetails(err error) string {
	return fmt.Sprintf("%+v", err)
}

func truncate(value string, maxBytes int) string {
	if len(value) <= maxBytes {
		return value
	}

	for maxBytes > 0 && !utf8.RuneStart(value[maxBytes]) {
		maxBytes--
	}

	return value[:maxBytes]
}
