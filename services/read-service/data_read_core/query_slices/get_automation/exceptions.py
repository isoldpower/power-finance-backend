from data_read_core.shared.http_contract import NotFound


class AutomationNotFoundError(NotFound):
    """404, including when the rule exists but belongs to someone else."""

    message = "Automation does not exist"
