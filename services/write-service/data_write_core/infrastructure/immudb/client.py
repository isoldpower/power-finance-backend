from immudb import ImmudbClient

from data_write_core.application.bootstrap.state import ImmudbConnection

from .database_schema import build_database


def build_immudb_client(
    host: str, port: int, username: str, password: str, transactions_db: str = "transactions"
) -> ImmudbConnection:
    client = ImmudbClient(immudUrl=f"{host}:{port}", timeout=3000)
    client.login(username=username, password=password)

    transaction_database = build_database(client, transactions_db)

    return ImmudbConnection(
        client=client,
        transaction_token=transaction_database,
    )
