package compression

import "github.com/twmb/franz-go/pkg/kgo"

type noCompression struct{}

func (noCompression) Codec() kgo.CompressionCodec {
	return kgo.NoCompression()
}
