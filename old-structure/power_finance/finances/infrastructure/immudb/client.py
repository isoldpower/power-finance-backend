from immudb import ImmudbClient
from immudb.datatypesv2 import DatabaseSettingsV2
from immudb.handler.useDatabase import dbUseResponse

from finances.application.bootstrap.state import ImmudbConnection


def _build_transaction_database(
        client: ImmudbClient,
        transaction_db: str,
) -> dbUseResponse:
    client.createDatabaseV2(
        name=transaction_db,
        settings=DatabaseSettingsV2(),
        ifNotExists=True,
    )
    response = client.useDatabase(bytes(transaction_db, "utf-8"))
    client.sqlExec('\
        CREATE TABLE IF NOT EXISTS transactions ( \
        id                  VARCHAR[36]  NOT NULL, \
        user_id             INTEGER      NOT NULL, \
        source_wallet_id    VARCHAR[36]  NOT NULL, \
        amount              VARCHAR[32]  NOT NULL, \
        created_at          VARCHAR[32]  NOT NULL, \
        cancels_other       VARCHAR[36], \
        adjusts_other       VARCHAR[36], \
        PRIMARY KEY id); \
    ')
    for col in ('cancels_other VARCHAR[36]', 'adjusts_other VARCHAR[36]'):
        try:
            client.sqlExec(f'ALTER TABLE transactions ADD COLUMN {col};')
        except Exception:
            pass
    client.sqlExec('\
        CREATE INDEX IF NOT EXISTS ON transactions(user_id); \
        CREATE INDEX IF NOT EXISTS ON transactions(source_wallet_id); \
    ')
    client.sqlExec('\
        CREATE TABLE IF NOT EXISTS balance_checkpoints ( \
        wallet_id     VARCHAR[36]  NOT NULL, \
        balance       VARCHAR[32]  NOT NULL, \
        currency      VARCHAR[8]   NOT NULL, \
        settled_at    VARCHAR[32]  NOT NULL, \
        last_tx_id    VARCHAR[36], \
        PRIMARY KEY   wallet_id \
    );')

    return response


def build_immudb_client(
        host: str,
        port: int,
        username: str,
        password: str,
        transactions_db: str = "transactions"
) -> ImmudbConnection:
    client = ImmudbClient(immudUrl=f"{host}:{port}", timeout=3000)
    client.login(username=username, password=password)

    transaction_database = _build_transaction_database(client, transactions_db)

    return ImmudbConnection(
        client=client,
        transaction_token=transaction_database,
    )