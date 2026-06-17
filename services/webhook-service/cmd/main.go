package main

import (
	"os"

	"services/webhook-service/cmd/cli"
	"services/webhook-service/internal/logging"
)

func main() {
	logging.Setup()

	if err := cli.NewCommand().Execute(); err != nil {
		os.Exit(1)
	}
}
