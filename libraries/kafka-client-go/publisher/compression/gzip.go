package compression

import "github.com/twmb/franz-go/pkg/kgo"

type gzipCompression struct{}

func (gzipCompression) Codec() kgo.CompressionCodec {
	return kgo.GzipCompression()
}
