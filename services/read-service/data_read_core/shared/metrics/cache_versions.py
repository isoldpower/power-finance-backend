from data_read_core.shared.redis_cache import get_redis

TRANSACTION_VERSION_KEY = "ver:transactions:{user_id}"
ACCOUNT_VERSION_KEY = "ver:accounts:{user_id}"


def get_transaction_version_key(user_id: int) -> str:
    return TRANSACTION_VERSION_KEY.format(user_id=user_id)


def get_account_version_key(user_id: int) -> str:
    return ACCOUNT_VERSION_KEY.format(user_id=user_id)


async def metrics_version(user_id: int) -> str:
    redis = get_redis()
    transactions, accounts = await redis.mget(
        get_transaction_version_key(user_id),
        get_account_version_key(user_id),
    )

    return f"{_as_version(transactions)}.{_as_version(accounts)}"


def _as_version(raw: str | None) -> int:
    return int(raw) if raw is not None else 0
