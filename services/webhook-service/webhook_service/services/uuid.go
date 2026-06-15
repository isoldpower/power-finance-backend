package services

import (
	"crypto/rand"
	"encoding/hex"
)

func newUUID() string {
	bytes := make([]byte, 16)
	_, _ = rand.Read(bytes)

	bytes[6] = (bytes[6] & 0x0f) | 0x40
	bytes[8] = (bytes[8] & 0x3f) | 0x80

	encoded := hex.EncodeToString(bytes)
	return encoded[0:8] + "-" + encoded[8:12] + "-" + encoded[12:16] + "-" +
		encoded[16:20] + "-" + encoded[20:32]
}
