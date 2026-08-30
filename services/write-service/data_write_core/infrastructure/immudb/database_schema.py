from immudb import ImmudbClient
from immudb.datatypesv2 import DatabaseSettingsV2
from immudb.handler.useDatabase import dbUseResponse

# Columns added after this table first shipped. `CREATE TABLE IF NOT EXISTS`
# leaves an existing table alone, so a volume older than the column keeps
# answering "column does not exist" until it is added explicitly. They are
# nullable here even where the CREATE says NOT NULL: immudb refuses to add a
# NOT NULL column to a table that already holds rows.
_TRANSACTIONS_ADDED_COLUMNS: tuple[tuple[str, str], ...] = (("transaction_id", "VARCHAR[36]"),)


def build_database(
    client: ImmudbClient,
    transaction_db: str,
) -> dbUseResponse:
    client.createDatabaseV2(
        name=transaction_db,
        settings=DatabaseSettingsV2(),
        ifNotExists=True,
    )
    response = client.useDatabase(bytes(transaction_db, "utf-8"))
    _initialize_schema(client)

    return response


def _initialize_schema(client: ImmudbClient) -> None:
    client.sqlExec(
        "\
        CREATE TABLE IF NOT EXISTS transactions ( \
        id                  VARCHAR[36]  NOT NULL, \
        user_id             INTEGER      NOT NULL, \
        transaction_id      VARCHAR[36]  NOT NULL, \
        source_wallet_id    VARCHAR[36]  NOT NULL, \
        amount              VARCHAR[32]  NOT NULL, \
        created_at          VARCHAR[32]  NOT NULL, \
        cancels_other       VARCHAR[36], \
        adjusts_other       VARCHAR[36], \
        PRIMARY KEY id); \
    "
    )

    _add_missing_columns(client, "transactions", _TRANSACTIONS_ADDED_COLUMNS)

    client.sqlExec(
        "\
        CREATE INDEX IF NOT EXISTS ON transactions(user_id); \
        CREATE INDEX IF NOT EXISTS ON transactions(transaction_id); \
        CREATE INDEX IF NOT EXISTS ON transactions(source_wallet_id); \
        CREATE INDEX IF NOT EXISTS ON transactions(cancels_other); \
    "
    )
    client.sqlExec(
        "\
        CREATE TABLE IF NOT EXISTS balance_checkpoints ( \
        wallet_id     VARCHAR[36]  NOT NULL, \
        balance       VARCHAR[32]  NOT NULL, \
        currency      VARCHAR[8]   NOT NULL, \
        settled_at    VARCHAR[32]  NOT NULL, \
        last_tx_id    VARCHAR[36], \
        PRIMARY KEY   wallet_id \
    );"
    )


def _add_missing_columns(
    client: ImmudbClient,
    table: str,
    columns: tuple[tuple[str, str], ...],
) -> None:
    existing = {row[1] for row in client.sqlQuery(f"SELECT * FROM COLUMNS('{table}');")}

    for name, definition in columns:
        if name not in existing:
            client.sqlExec(f"ALTER TABLE {table} ADD COLUMN {name} {definition};")
