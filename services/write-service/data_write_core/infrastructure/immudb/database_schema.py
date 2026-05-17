from immudb import ImmudbClient
from immudb.datatypesv2 import DatabaseSettingsV2
from immudb.handler.useDatabase import dbUseResponse


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
        source_wallet_id    VARCHAR[36]  NOT NULL, \
        amount              VARCHAR[32]  NOT NULL, \
        created_at          VARCHAR[32]  NOT NULL, \
        cancels_other       VARCHAR[36], \
        adjusts_other       VARCHAR[36], \
        PRIMARY KEY id); \
    "
    )

    client.sqlExec("ALTER TABLE users ADD COLUMN cancels_other VARCHAR[36];")
    client.sqlExec("ALTER TABLE users ADD COLUMN adjusts_other VARCHAR[36];")
    client.sqlExec(
        "\
        CREATE INDEX IF NOT EXISTS ON transactions(user_id); \
        CREATE INDEX IF NOT EXISTS ON transactions(source_wallet_id); \
        CREATE UNIQUE INDEX IF NOT EXISTS ON transactions(cancels_other); \
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
