from enum import StrEnum

REPORT_NAME = "get_analytics_money_flow"


class FlowNodeKind(StrEnum):
    INCOME_CATEGORY = "income_category"
    WALLET = "wallet"
    EXPENSE_CATEGORY = "expense_category"
    SAVINGS = "savings"
    RESERVES = "reserves"


class FlowNodeIdentifiers(StrEnum):
    SAVINGS = "savings"
    RESERVES = "reserves"
    INCOME_PREFIX = "income:"
    WALLET_PREFIX = "wallet:"
    EXPENSE_PREFIX = "expense:"


class FlowNodeLabels(StrEnum):
    SAVINGS = "Saved"
    RESERVES = "From balance"
    UNCATEGORISED = "Uncategorized"
