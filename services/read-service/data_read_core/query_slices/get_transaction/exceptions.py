from data_read_core.shared.http_contract import NotFound


class TransactionNotFoundError(NotFound):
    message = "Transaction does not exist"
