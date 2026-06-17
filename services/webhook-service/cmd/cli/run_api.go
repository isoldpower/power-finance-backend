package cli

import (
	"github.com/spf13/cobra"

	"services/webhook-service/cmd/config"
	"services/webhook-service/webhook_service"
)

// RunAPICommand boots the webhook delivery pipeline together with its HTTP
// server and blocks until shutdown.
type RunAPICommand struct {
	commandInstance *cobra.Command
}

// NewRunAPICommand builds the `run-api` subcommand.
func NewRunAPICommand() *RunAPICommand {
	command := &RunAPICommand{}

	command.commandInstance = &cobra.Command{
		Use:   "run-api",
		Short: "Run the webhook-service HTTP API, Kafka consumer and delivery workers",
		Long:  "Boots the webhook delivery pipeline (Kafka consumer, dispatcher, retry scheduler) and the HTTP server, then blocks until shutdown.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return webhook_service.StartWebhookService(config.Load())
		},
	}

	return command
}

// Register attaches the `run-api` command to the given parent.
func (rc *RunAPICommand) Register(parentCmd *cobra.Command) {
	parentCmd.AddCommand(rc.commandInstance)
}
