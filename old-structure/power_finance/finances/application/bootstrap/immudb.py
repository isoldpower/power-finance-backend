from .state import ApplicationEnvironment, ImmudbConnection

from finances.infrastructure.immudb import build_immudb_client


def initialize_immudb(environment: ApplicationEnvironment) -> ImmudbConnection:
    return build_immudb_client(
        host=environment.immudb_host,
        port=environment.immudb_port,
        username=environment.immudb_user,
        password=environment.immudb_password,
        transactions_db=environment.immudb_transactions_database,
    )