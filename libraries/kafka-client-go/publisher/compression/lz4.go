package compression

import "github.com/twmb/franz-go/pkg/kgo"

type lz4Compression struct{}

func (lz4Compression) Codec() kgo.CompressionCodec {
	return kgo.Lz4Compression()
}
