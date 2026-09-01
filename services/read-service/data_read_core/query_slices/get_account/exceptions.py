from data_read_core.shared.http_contract import NotFound


class AccountNotFoundError(NotFound):
    """404, including when the row exists but belongs to someone else."""

    message = "Account does not exist"
