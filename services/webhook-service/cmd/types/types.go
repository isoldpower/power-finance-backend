package types

import "github.com/spf13/cobra"

// SubCommand is implemented by every command that attaches itself to a parent
// command via Register.
type SubCommand interface {
	Register(parentCmd *cobra.Command)
}

// Command is the root CLI entry-point contract.
type Command interface {
	Execute() error
}
