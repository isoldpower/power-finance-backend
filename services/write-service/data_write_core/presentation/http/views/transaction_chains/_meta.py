from typing import Any

from write_service.common.pagination import DEFAULT_LIMIT_POLICY, Page

TRANSACTIONS_NAMESPACE = "transactions"


def chain_meta(total: int, **extra: Any) -> dict[str, Any]:
    whole_chain = Page(items=[], total=total, limit=DEFAULT_LIMIT_POLICY.default)

    return {**whole_chain.meta(namespace=TRANSACTIONS_NAMESPACE), **extra}
