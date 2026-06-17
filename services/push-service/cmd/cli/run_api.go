package cli

import (
	"github.com/spf13/cobra"

	"services/push-service/cmd/config"
	"services/push-service/internal/logging"
	"services/push-service/push_service"
)

// RunAPICommand boots the push-service HTTP API together with its Kafka
// broadcast consumer and blocks until shutdown.
type RunAPICommand struct {
	commandInstance *cobra.Command
}

// NewRunAPICommand builds the `run-api` subcommand.
func NewRunAPICommand() *RunAPICommand {
	command := &RunAPICommand{}

	command.commandInstance = &cobra.Command{
		Use:   "run-api",
		Short: "Run the push-service HTTP API and Kafka consumer",
		Long:  "Boots the SSE notifications API and the Kafka broadcast consumer, then blocks until shutdown.",
		RunE: func(cmd *cobra.Command, args []string) error {
			serviceConfig := config.Load()
			logging.SetLevel(serviceConfig.Logging.Level)

			return push_service.StartPushService(serviceConfig)
		},
	}

	return command
}

// Register attaches the `run-api` command to the given parent.
func (rc *RunAPICommand) Register(parentCmd *cobra.Command) {
	parentCmd.AddCommand(rc.commandInstance)
}
