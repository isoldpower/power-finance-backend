"""Field policies, keyed by the resource they govern."""

from ..entities import FilterPolicy
from .transactions import TRANSACTION_FILTER_POLICY
from .wallets import WALLET_FILTER_POLICY
from .webhooks import WEBHOOK_FILTER_POLICY


class FilterResource:
    TRANSACTIONS = "transactions"
    WALLETS = "wallets"
    WEBHOOKS = "webhooks"


FILTER_POLICIES: dict[str, FilterPolicy] = {
    FilterResource.TRANSACTIONS: TRANSACTION_FILTER_POLICY,
    FilterResource.WALLETS: WALLET_FILTER_POLICY,
    FilterResource.WEBHOOKS: WEBHOOK_FILTER_POLICY,
}


def policy_for(resource: str) -> FilterPolicy:
    return FILTER_POLICIES[resource]


__all__ = [
    "FILTER_POLICIES",
    "TRANSACTION_FILTER_POLICY",
    "WALLET_FILTER_POLICY",
    "WEBHOOK_FILTER_POLICY",
    "FilterResource",
    "policy_for",
]
