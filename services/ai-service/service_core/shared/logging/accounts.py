from .registry import get_service_logger

_logger = get_service_logger("accounts")


def log_template_accounts_seeded(user_id: int, account_count: int) -> None:
    _logger.info("seeded %s template accounts for user %s", account_count, user_id)


def log_balances_recomputed(account_count: int) -> None:
    _logger.debug("recomputed %s account balances", account_count)
