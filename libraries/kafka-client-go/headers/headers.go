package headers

import (
	"strconv"
	"time"
)

const (
	OriginalTopic     = "x-original-topic"
	OriginalPartition = "x-original-partition"
	OriginalOffset    = "x-original-offset"

	RetryCount    = "x-retry-count"
	RetryAt       = "x-retry-at"
	FirstFailedAt = "x-first-failed-at"

	ErrorClass   = "x-error-class"
	ErrorMessage = "x-error-message"
	ErrorStack   = "x-error-stack"
	FailedAt     = "x-failed-at"

	CorrelationID = "x-correlation-id"
)

type Header struct {
	Key   string
	Value []byte
}

type KafkaHeaders []Header

func String(key string, value string) Header {
	return Header{Key: key, Value: []byte(value)}
}

func Int(key string, value int64) Header {
	return Header{Key: key, Value: []byte(strconv.FormatInt(value, 10))}
}

func Time(key string, value time.Time) Header {
	return Header{Key: key, Value: []byte(EncodeTime(value))}
}

func EncodeTime(value time.Time) string {
	return value.UTC().Format(time.RFC3339Nano)
}

func Get(headers KafkaHeaders, name string) (string, bool) {
	var lastMatch []byte
	isFound := false
	for _, header := range headers {
		if header.Key == name {
			lastMatch = header.Value
			isFound = true
		}
	}

	if !isFound {
		return "", false
	}

	return string(lastMatch), true
}

func GetInt(headers KafkaHeaders, name string, defaultValue int) int {
	rawHeaderValue, isFound := Get(headers, name)
	if !isFound {
		return defaultValue
	}

	parsedValue, parseErr := strconv.Atoi(rawHeaderValue)
	if parseErr != nil {
		return defaultValue
	}

	return parsedValue
}

func GetTime(headers KafkaHeaders, name string) (time.Time, bool) {
	rawHeaderValue, isFound := Get(headers, name)
	if !isFound {
		return time.Time{}, false
	}

	parsedTime, parseErr := time.Parse(time.RFC3339Nano, rawHeaderValue)
	if parseErr != nil {
		return time.Time{}, false
	}

	return parsedTime, true
}

func Merge(base KafkaHeaders, additions ...Header) KafkaHeaders {
	mergedHeaders := make(KafkaHeaders, 0, len(base)+len(additions))
	mergedHeaders = append(mergedHeaders, base...)
	mergedHeaders = append(mergedHeaders, additions...)

	return mergedHeaders
}
