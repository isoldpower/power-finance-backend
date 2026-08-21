from data_read_core.shared.http_contract import NotFound


class WalletNotFoundError(NotFound):
    """404, including when the row exists but belongs to someone else."""

    message = "Wallet does not exist"
