def get_single_wallet_key(wallet_id: str) -> str:
    return f"read:wallet:{wallet_id}"


def get_wallet_list_version_key(user_id: int) -> str:
    return f"ver:wallets:{user_id}"


def get_single_transaction_key(transaction_id: str) -> str:
    return f"read:transaction:{transaction_id}"


def get_transaction_list_version_key(user_id: int) -> str:
    return f"ver:transactions:{user_id}"


def get_single_notification_key(notification_id: str) -> str:
    return f"read:notification:{notification_id}"


def get_notification_list_version_key(user_id: int) -> str:
    return f"ver:notifications:{user_id}"


def get_single_webhook_key(webhook_id: str) -> str:
    return f"read:webhook:{webhook_id}"


def get_webhook_list_version_key(user_id: int) -> str:
    return f"ver:webhooks:{user_id}"


def get_webhook_events_key(webhook_id: str) -> str:
    return f"read:webhook_events:{webhook_id}"
