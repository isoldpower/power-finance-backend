package cli

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"services/webhook-service/cmd/types"
)

// RootCommand is the top-level CLI for the webhook-service control plane.
type RootCommand struct {
	commandInstance *cobra.Command
}

// NewCommand assembles the root command and wires up every subcommand.
func NewCommand() *RootCommand {
	rootCommand := &RootCommand{
		commandInstance: &cobra.Command{
			Use:           "webhook-service",
			Short:         "Webhook Service control plane",
			Version:       "1.0.0",
			SilenceErrors: true,
			SilenceUsage:  true,
			Run: func(cmd *cobra.Command, args []string) {
				cmd.HelpFunc()(cmd, args)
			},
		},
	}

	subcommands := []types.SubCommand{
		NewRunAPICommand(),
		NewMigrateCommand(),
	}
	for _, subcommand := range subcommands {
		subcommand.Register(rootCommand.commandInstance)
	}

	return rootCommand
}

// Execute is the entry-point that starts CLI dispatch and reports failures.
func (c *RootCommand) Execute() error {
	if err := c.commandInstance.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		logCLIExecutionFailed(err)

		return err
	}

	return nil
}
