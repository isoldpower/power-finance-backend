package main

import (
	"os"

	"services/push-service/cmd/cli"
	"services/push-service/internal/logging"
)

func main() {
	logging.Setup()

	if err := cli.NewCommand().Execute(); err != nil {
		os.Exit(1)
	}
}
