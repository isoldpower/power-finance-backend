from data_write_core.infrastructure.immudb.client import build_immudb_client

from .state import ApplicationEnvironment, ImmudbConnection


def initialize_immudb(environment: ApplicationEnvironment) -> ImmudbConnection:
    return build_immudb_client(
        host=environment.immudb_host,
        port=environment.immudb_port,
        username=environment.immudb_user,
        password=environment.immudb_password,
        transactions_db=environment.immudb_transactions_db,
    )
