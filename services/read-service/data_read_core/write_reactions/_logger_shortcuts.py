from decimal import Decimal

from data_read_core.shared.logging import get_workers_logger


def warn_no_outbox_sequence(event_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")

    logger.warning(
        "Event %s carries no outbox seq; projecting without advancing "
        "read-your-writes progress.",
        event_id,
    )


def except_service_model_mismatch(resource_id: object) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.fatal(
        "Received a resource (id %s) that is breaking read model's schema unique constraints. "
        "It may mean that models are not properly aligned or deduplication failed.",
        resource_id,
    )


def except_constraint_violation(resource_id: object) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.fatal(
        "Received a resource (id %s) that is breaking read model's schema unique constraints. "
        "It may mean that models are not properly aligned or deduplication failed.",
        resource_id,
    )


def log_transaction_elastic_created(transaction_id: str, index: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Projected transaction %s into Elasticsearch-based index %s.",
        transaction_id,
        index,
    )


def log_transaction_elastic_removed(transaction_id: str, index: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Removed transaction %s from Elasticsearch-based index %s.",
        transaction_id,
        index,
    )


def log_transaction_elastic_updated(transaction_id: str, index: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Updated transaction %s inside Elasticsearch-based index %s.",
        transaction_id,
        index,
    )


def log_transaction_postgres_duplication(transaction_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Transaction %s already projected into Postgres; skipping balance adjustment.",
        transaction_id,
    )


def log_transaction_postgres_created(transaction_id: str, amount: float) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Created transaction %s inside Postgres-based table with value %s.",
        transaction_id,
        amount,
    )


def log_transaction_postgres_container_update(
    container_id: str,
    amount: float,
    count: int,
) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Adjusted container %s running total by %s (rows=%s).",
        container_id,
        amount,
        count,
    )


def log_transaction_postgres_absent_on_delete(transaction_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Transaction %s not present; skipping balance reversal.",
        transaction_id,
    )


def log_transaction_postgres_removed(transaction_id: str, amount: Decimal) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Removed transaction %s with value of %s.",
        transaction_id,
        amount,
    )


def log_transaction_postgres_container_reversal(wallet_id: str, amount: Decimal) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Reversed wallet %s balance by %s.",
        wallet_id,
        amount,
    )


def log_transaction_postgres_absent_on_update(transaction_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Transaction %s not present; skipping update.",
        transaction_id,
    )


def log_transaction_postgres_unchanged(transaction_id: str, amount: Decimal) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Transaction %s already at amount %s; skipping.",
        transaction_id,
        amount,
    )


def log_transaction_postgres_updated(
    transaction_id: str,
    new_amount: Decimal,
    wallet_id: str,
    amount_delta: Decimal,
) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Updated transaction %s amount to %s and adjusted wallet %s balance by %s.",
        transaction_id,
        new_amount,
        wallet_id,
        amount_delta,
    )


def log_transaction_list_version_bumped(user_id: int, version: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Bumped transaction list version for user %s to %s.",
        user_id,
        version,
    )


def log_transaction_cache_evicted(key: str, removed: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Evicted cache key %s (removed=%s).",
        key,
        removed,
    )


def log_wallet_elastic_created(wallet_id: str, index: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Indexed wallet %s into %s.",
        wallet_id,
        index,
    )


def log_wallet_elastic_removed(wallet_id: str, index: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Removed wallet %s from %s.",
        wallet_id,
        index,
    )


def log_wallet_elastic_updated(wallet_id: str, index: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Updated wallet %s in %s.",
        wallet_id,
        index,
    )


def log_wallet_postgres_created(wallet_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Received WalletCreated payload for wallet %s.",
        wallet_id,
    )


def log_wallet_postgres_removed(wallet_id: str, count: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Removed wallet %s from read store (rows=%s).",
        wallet_id,
        count,
    )


def log_wallet_postgres_updated(wallet_id: str, count: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Updated wallet %s in read store (rows=%s).",
        wallet_id,
        count,
    )


def log_wallet_list_version_bumped(user_id: int, version: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Bumped wallet list version for user %s to %s.",
        user_id,
        version,
    )


def log_wallet_cache_evicted(key: str, removed: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Evicted cache key %s (removed=%s).",
        key,
        removed,
    )


def log_user_projected(user_id: int, external_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Projected user %s (external %s).",
        user_id,
        external_id,
    )


def log_notification_postgres_created(notification_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Received NotificationCreated payload for notification %s.",
        notification_id,
    )


def log_notification_postgres_acknowledged(notification_ids: list[str], count: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Acknowledged notifications %s in read store (rows=%s).",
        notification_ids,
        count,
    )


def log_notification_postgres_removed(notification_id: str, count: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Removed notification %s from read store (rows=%s).",
        notification_id,
        count,
    )


def log_notification_list_version_bumped(user_id: int, version: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Bumped notification list version for user %s to %s.",
        user_id,
        version,
    )


def log_notification_cache_evicted(key: str, removed: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Evicted cache key %s (removed=%s).",
        key,
        removed,
    )


def log_webhook_postgres_created(webhook_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Received WebhookEndpointCreated payload for webhook %s.",
        webhook_id,
    )


def log_webhook_postgres_updated(webhook_id: str, count: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Updated webhook %s in read store (rows=%s).",
        webhook_id,
        count,
    )


def log_webhook_postgres_removed(webhook_id: str, count: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Removed webhook %s from read store (rows=%s).",
        webhook_id,
        count,
    )


def log_webhook_subscription_postgres_created(subscription_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Received WebhookSubscriptionAdded payload for subscription %s.",
        subscription_id,
    )


def log_webhook_subscription_postgres_removed(subscription_id: str, count: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Removed webhook subscription %s from read store (rows=%s).",
        subscription_id,
        count,
    )


def log_webhook_list_version_bumped(user_id: int, version: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Bumped webhook list version for user %s to %s.",
        user_id,
        version,
    )


def log_webhook_cache_evicted(key: str, removed: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Evicted cache key %s (removed=%s).",
        key,
        removed,
    )


def log_transaction_postgres_metadata_updated(transaction_id: str, rows: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Updated transaction %s metadata (rows=%s).",
        transaction_id,
        rows,
    )


def log_wallet_name_denormalised(wallet_id: str, rows: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Carried wallet %s rename into %s transaction rows.",
        wallet_id,
        rows,
    )


def log_goal_postgres_created(goal_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Received GoalCreated payload for goal %s.",
        goal_id,
    )


def log_goal_postgres_removed(goal_id: str, count: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Closed goal %s in read store (rows=%s).",
        goal_id,
        count,
    )


def log_goal_postgres_updated(goal_id: str, count: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Updated goal %s in read store (rows=%s).",
        goal_id,
        count,
    )


def log_goal_list_version_bumped(user_id: int, version: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Bumped goal list version for user %s to %s.",
        user_id,
        version,
    )


def log_goal_cache_evicted(key: str, removed: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Evicted cache key %s (removed=%s).",
        key,
        removed,
    )


def log_goal_transactions_renamed(goal_id: str, count: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Renamed goal %s across its transactions (rows=%s).",
        goal_id,
        count,
    )


def log_account_postgres_created(account_id: str, name: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info("Projected account %s (%s) into Postgres.", account_id, name)


def log_account_postgres_duplication(account_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info("Account %s was already projected; redelivery ignored.", account_id)


def log_account_postgres_updated(account_id: str, balance: Decimal) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info("Restated account %s balance to %s.", account_id, balance)


def log_posting_postgres_created(posting_id: str, transaction_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info("Projected posting %s of transaction %s.", posting_id, transaction_id)


def log_posting_postgres_duplication(posting_id: str) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info("Posting %s was already projected; redelivery ignored.", posting_id)


def log_posting_postgres_removed(posting_id: str, removed_count: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info("Removed %s row(s) for posting %s.", removed_count, posting_id)


def log_dispatch_postgres_recorded(transaction_id: str, balanced: bool) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info(
        "Recorded dispatch verdict for transaction %s (balanced=%s).",
        transaction_id,
        balanced,
    )


def log_account_list_version_bumped(user_id: int, version: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info("Bumped account list version for user %s to %s.", user_id, version)


def log_account_postings_version_bumped(account_id: str, version: int) -> None:
    logger = get_workers_logger("write_message_consumer")
    logger.info("Bumped posting list version for account %s to %s.", account_id, version)
