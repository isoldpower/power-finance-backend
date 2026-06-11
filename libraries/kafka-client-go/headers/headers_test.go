package headers

import (
	"testing"
	"time"
)

func TestGetReturnsLastMatch(t *testing.T) {
	kafkaHeaders := KafkaHeaders{
		String(RetryCount, "1"),
		String(RetryCount, "2"),
	}

	value, found := Get(kafkaHeaders, RetryCount)

	if !found {
		t.Fatal("expected header to be found")
	}
	if value != "2" {
		t.Fatalf("expected last match %q, got %q", "2", value)
	}
}

func TestGetMissing(t *testing.T) {
	_, found := Get(KafkaHeaders{}, "x-missing")

	if found {
		t.Fatal("expected header to be missing")
	}
}

func TestGetIntParsesValue(t *testing.T) {
	kafkaHeaders := KafkaHeaders{Int(RetryCount, 7)}

	if got := GetInt(kafkaHeaders, RetryCount, 0); got != 7 {
		t.Fatalf("expected 7, got %d", got)
	}
}

func TestGetIntReturnsDefaultOnMissingOrInvalid(t *testing.T) {
	if got := GetInt(KafkaHeaders{}, RetryCount, 9); got != 9 {
		t.Fatalf("expected default 9 on missing header, got %d", got)
	}

	invalid := KafkaHeaders{String(RetryCount, "not-a-number")}
	if got := GetInt(invalid, RetryCount, 9); got != 9 {
		t.Fatalf("expected default 9 on invalid header, got %d", got)
	}
}

func TestGetTimeRoundTrip(t *testing.T) {
	stamped := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	kafkaHeaders := KafkaHeaders{Time(FirstFailedAt, stamped)}

	parsed, found := GetTime(kafkaHeaders, FirstFailedAt)

	if !found {
		t.Fatal("expected header to be found")
	}
	if !parsed.Equal(stamped) {
		t.Fatalf("expected %v, got %v", stamped, parsed)
	}
}

func TestGetTimeParsesPythonIsoformat(t *testing.T) {
	pythonEncodedTimestamps := map[string]time.Time{
		"2026-01-02T03:04:05+00:00":        time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC),
		"2026-01-02T03:04:05.123456+00:00": time.Date(2026, 1, 2, 3, 4, 5, 123456000, time.UTC),
	}

	for encoded, expected := range pythonEncodedTimestamps {
		kafkaHeaders := KafkaHeaders{String(FirstFailedAt, encoded)}

		parsed, found := GetTime(kafkaHeaders, FirstFailedAt)

		if !found {
			t.Fatalf("expected %q to be parsed", encoded)
		}
		if !parsed.Equal(expected) {
			t.Fatalf("expected %v for %q, got %v", expected, encoded, parsed)
		}
	}
}

func TestGetTimeInvalidValue(t *testing.T) {
	kafkaHeaders := KafkaHeaders{String(FirstFailedAt, "not-a-timestamp")}

	if _, found := GetTime(kafkaHeaders, FirstFailedAt); found {
		t.Fatal("expected invalid timestamp to be treated as missing")
	}
}

func TestEncodeTimeNormalizesToUTC(t *testing.T) {
	plusTwo := time.FixedZone("UTC+2", 2*60*60)
	localTime := time.Date(2026, 1, 2, 5, 0, 0, 0, plusTwo)

	if got := EncodeTime(localTime); got != "2026-01-02T03:00:00Z" {
		t.Fatalf("expected UTC-normalized timestamp, got %q", got)
	}
}

func TestMergeAppendsWithoutMutatingBase(t *testing.T) {
	base := KafkaHeaders{String("a", "1")}

	merged := Merge(base, String("b", "2"), Int("c", 3))

	if len(base) != 1 {
		t.Fatalf("expected base untouched, got %d headers", len(base))
	}
	if len(merged) != 3 {
		t.Fatalf("expected 3 merged headers, got %d", len(merged))
	}
	if value, _ := Get(merged, "c"); value != "3" {
		t.Fatalf("expected encoded int %q, got %q", "3", value)
	}
}

func TestMergeNilBase(t *testing.T) {
	merged := Merge(nil, String("a", "1"))

	if len(merged) != 1 {
		t.Fatalf("expected 1 header, got %d", len(merged))
	}
}

func TestGetTimeMissingHeader(t *testing.T) {
	if _, found := GetTime(KafkaHeaders{}, FirstFailedAt); found {
		t.Fatal("expected missing header to report not found")
	}
}

func TestGetOnNilHeaders(t *testing.T) {
	if _, found := Get(nil, RetryCount); found {
		t.Fatal("expected nil headers to report not found")
	}
}
