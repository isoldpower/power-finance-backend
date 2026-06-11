package compression

import (
	"testing"

	"github.com/twmb/franz-go/pkg/kgo"
)

func TestTypesMapToFranzGoCodecs(t *testing.T) {
	cases := map[string]struct {
		compressionType CompressionType
		expectedCodec   kgo.CompressionCodec
	}{
		"none":   {compressionType: CompressionNone, expectedCodec: kgo.NoCompression()},
		"gzip":   {compressionType: CompressionGzip, expectedCodec: kgo.GzipCompression()},
		"snappy": {compressionType: CompressionSnappy, expectedCodec: kgo.SnappyCompression()},
		"lz4":    {compressionType: CompressionLz4, expectedCodec: kgo.Lz4Compression()},
		"zstd":   {compressionType: CompressionZstd, expectedCodec: kgo.ZstdCompression()},
	}

	for name, testCase := range cases {
		if got := testCase.compressionType.Codec(); got != testCase.expectedCodec {
			t.Fatalf("%s: expected codec %v, got %v", name, testCase.expectedCodec, got)
		}
	}
}

func TestEachTypeProducesDistinctCodec(t *testing.T) {
	seen := map[kgo.CompressionCodec]bool{}
	for _, compressionType := range []CompressionType{
		CompressionNone,
		CompressionGzip,
		CompressionSnappy,
		CompressionLz4,
		CompressionZstd,
	} {
		codec := compressionType.Codec()
		if seen[codec] {
			t.Fatalf("duplicate codec %v", codec)
		}
		seen[codec] = true
	}
}
