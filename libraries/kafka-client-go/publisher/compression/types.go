package compression

import "github.com/twmb/franz-go/pkg/kgo"

type CompressionType interface {
	Codec() kgo.CompressionCodec
}

var (
	CompressionNone   CompressionType = noCompression{}
	CompressionGzip   CompressionType = gzipCompression{}
	CompressionSnappy CompressionType = snappyCompression{}
	CompressionLz4    CompressionType = lz4Compression{}
	CompressionZstd   CompressionType = zstdCompression{}
)
