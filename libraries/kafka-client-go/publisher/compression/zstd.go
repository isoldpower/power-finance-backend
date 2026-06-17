package compression

import "github.com/twmb/franz-go/pkg/kgo"

type zstdCompression struct{}

func (zstdCompression) Codec() kgo.CompressionCodec {
	return kgo.ZstdCompression()
}
