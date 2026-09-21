from data_read_core.shared.http_contract import NotFound


class WalletNotFoundError(NotFound):
    message = "Wallet does not exist"
