package cli

import (
	"context"
	"database/sql"
	"fmt"

	_ "github.com/jackc/pgx/v5/stdlib" // database/sql driver named "pgx"
	"github.com/pressly/goose/v3"
	"github.com/spf13/cobra"

	"services/webhook-service/cmd/config"
	"services/webhook-service/webhook_service/migrations"
)

const (
	migrationsDir      = "."
	defaultMigrateVerb = "status"
)

// MigrateCommand runs the embedded Goose migrations against the configured
// Postgres database.
type MigrateCommand struct {
	commandInstance *cobra.Command
}

// NewMigrateCommand builds the `migrate` subcommand.
func NewMigrateCommand() *MigrateCommand {
	command := &MigrateCommand{}

	command.commandInstance = &cobra.Command{
		Use:   "migrate [up | down | status | up-by-one | reset | version]",
		Short: "Run Goose database migrations",
		Long:  "Applies the embedded Goose migrations against the configured Postgres database. Defaults to 'status' when no verb is given.",
		RunE: func(cmd *cobra.Command, args []string) error {
			verb := defaultMigrateVerb
			if len(args) > 0 {
				verb = args[0]
			}

			return runMigrations(cmd.Context(), verb, args[1:])
		},
	}

	return command
}

func runMigrations(ctx context.Context, verb string, verbArgs []string) error {
	dsn := config.Load().Postgres.DSN

	database, openErr := sql.Open("pgx", dsn)
	if openErr != nil {
		return fmt.Errorf("migrate: open database: %w", openErr)
	}
	defer database.Close()

	goose.SetBaseFS(migrations.FS)
	if dialectErr := goose.SetDialect("postgres"); dialectErr != nil {
		return fmt.Errorf("migrate: set dialect: %w", dialectErr)
	}

	if runErr := goose.RunContext(ctx, verb, database, migrationsDir, verbArgs...); runErr != nil {
		return fmt.Errorf("migrate: run %q: %w", verb, runErr)
	}

	return nil
}

// Register attaches the `migrate` command to the given parent.
func (mc *MigrateCommand) Register(parentCmd *cobra.Command) {
	parentCmd.AddCommand(mc.commandInstance)
}
