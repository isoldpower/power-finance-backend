package compression

import "github.com/twmb/franz-go/pkg/kgo"

type snappyCompression struct{}

func (snappyCompression) Codec() kgo.CompressionCodec {
	return kgo.SnappyCompression()
}
