"""Field policies, keyed by the resource they govern."""

from ..entities import FilterPolicy
from .automations import AUTOMATION_FILTER_POLICY
from .goals import GOAL_FILTER_POLICY
from .transactions import TRANSACTION_FILTER_POLICY
from .wallets import WALLET_FILTER_POLICY
from .webhooks import WEBHOOK_FILTER_POLICY


class FilterResource:
    AUTOMATIONS = "automations"
    GOALS = "goals"
    TRANSACTIONS = "transactions"
    WALLETS = "wallets"
    WEBHOOKS = "webhooks"


FILTER_POLICIES: dict[str, FilterPolicy] = {
    FilterResource.AUTOMATIONS: AUTOMATION_FILTER_POLICY,
    FilterResource.GOALS: GOAL_FILTER_POLICY,
    FilterResource.TRANSACTIONS: TRANSACTION_FILTER_POLICY,
    FilterResource.WALLETS: WALLET_FILTER_POLICY,
    FilterResource.WEBHOOKS: WEBHOOK_FILTER_POLICY,
}


def policy_for(resource: str) -> FilterPolicy:
    return FILTER_POLICIES[resource]


__all__ = [
    "AUTOMATION_FILTER_POLICY",
    "FILTER_POLICIES",
    "GOAL_FILTER_POLICY",
    "TRANSACTION_FILTER_POLICY",
    "WALLET_FILTER_POLICY",
    "WEBHOOK_FILTER_POLICY",
    "FilterResource",
    "policy_for",
]
