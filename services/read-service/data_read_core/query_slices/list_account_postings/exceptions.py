from data_read_core.shared.http_contract import NotFound


class AccountNotFoundError(NotFound):
    message = "Account does not exist"
