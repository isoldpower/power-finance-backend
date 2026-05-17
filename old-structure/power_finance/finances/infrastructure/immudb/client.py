from immudb import ImmudbClient
from immudb.datatypesv2 import DatabaseSettingsV2
from immudb.handler.useDatabase import dbUseResponse

from data_write_core.application.bootstrap.state import ImmudbConnection
from data_write_core.infrastructure.immudb.database_schema import initialize_schema


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
    initialize_schema(client)

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