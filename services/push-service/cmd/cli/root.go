package cli

import (
	"fmt"
	"log/slog"
	"os"

	"github.com/spf13/cobra"

	"services/push-service/cmd/types"
)

// RootCommand is the top-level CLI for the push-service control plane. It owns
// the cobra command tree and dispatches to the registered subcommands.
type RootCommand struct {
	commandInstance *cobra.Command
}

// NewCommand assembles the root command and wires up every subcommand.
func NewCommand() *RootCommand {
	rootCommand := &RootCommand{
		commandInstance: &cobra.Command{
			Use:           "push-service",
			Short:         "Push Service control plane",
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
		slog.Error("cli execution failed", "error", err)

		return err
	}

	return nil
}
