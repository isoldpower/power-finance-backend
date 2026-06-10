package utilities

import (
	"bytes"
	"encoding/gob"
)

func EncodeStructToBytes[T struct{}](value T) ([]byte, error) {
	buffer := bytes.NewBuffer(make([]byte, 0))
	enc := gob.NewEncoder(buffer)

	encodeErr := enc.Encode(value)
	if encodeErr != nil {
		return nil, encodeErr
	}

	return buffer.Bytes(), nil
}
