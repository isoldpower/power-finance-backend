"""Logger-name builders, context formatting, and request log helpers."""

from unittest.mock import Mock

from data_read_core.shared.logging import (
    get_main_logger,
    get_query_logger,
    get_workers_logger,
    log_request_failed,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.logging._format import _format_context


def test_format_context_empty_is_blank():
    assert _format_context({}) == ""


def test_format_context_joins_pairs():
    assert _format_context({"wallet_id": "w1", "user_id": 7}) == " (wallet_id=w1, user_id=7)"


def test_query_logger_is_namespaced():
    assert get_query_logger("get_wallet", "cache").name == "query_slices.get_wallet.cache"


def test_workers_logger_is_namespaced():
    assert get_workers_logger("health").name == "background_workers.health"


def test_main_logger_root_has_no_trailing_dot():
    assert get_main_logger().name == "data_read_core"


def test_log_request_received_uses_info():
    logger = Mock()
    log_request_received(logger, "list_wallets", user_id=7)
    logger.info.assert_called_once_with("%s: request received%s", "list_wallets", " (user_id=7)")


def test_log_request_served_uses_info():
    logger = Mock()
    log_request_served(logger, "list_wallets")
    logger.info.assert_called_once_with("%s: request served%s", "list_wallets", "")


def test_log_request_failed_uses_error_with_exception():
    logger = Mock()
    error = ValueError("boom")
    log_request_failed(logger, "get_wallet", error, wallet_id="w1")
    logger.error.assert_called_once_with(
        "%s: request failed%s — %s", "get_wallet", " (wallet_id=w1)", error
    )
