from data_read_core.shared.http_contract import NotFound


class AutomationNotFoundError(NotFound):
    message = "Automation does not exist"
