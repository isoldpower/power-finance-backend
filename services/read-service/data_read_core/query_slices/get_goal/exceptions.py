from data_read_core.shared.http_contract import NotFound


class GoalNotFoundError(NotFound):
    """404, including when the row exists but belongs to someone else."""

    pass
