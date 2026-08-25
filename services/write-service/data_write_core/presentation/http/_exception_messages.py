from enum import StrEnum

from django.core.exceptions import ObjectDoesNotExist

from data_write_core.application.exceptions import FallbackTransactionNotVisibleError
from data_write_core.domain import exceptions as domain

MISSING_RESOURCES = (
    ObjectDoesNotExist,
    FallbackTransactionNotVisibleError,
    domain.TransactionChainNotFoundError,
    domain.WebhookNotFoundError,
    domain.WebhookSubscriptionNotFoundError,
    domain.NotificationNotFoundError,
    domain.TransactionDoesNotBelongToWalletError,
    domain.MoneyContainerNotFoundError,
)


UNPROCESSABLE_STATES = (
    domain.TransactionDirectionChangeError,
    domain.ConflictingMoneyFlowDataError,
    domain.TransactionAlreadyAdjustedError,
    domain.CannotCancelInverseTransactionError,
    domain.CannotAdjustAdjustmentTransactionError,
)


class FIELDS(StrEnum):
    AMOUNT = "amount"
    CURRENCY = "currency"
    EVENT_TYPE = "event_type"
    CHAIN_ENTRY = "transactions[{index}].after"


class MESSAGES(StrEnum):
    ALREADY_CANCELLED = "Transaction has already been cancelled"
    DUPLICATE_SUBSCRIPTION = "Webhook already subscribes to that event"
    INSUFFICIENT_FUNDS = "Wallet does not hold enough funds for this transaction"
    WALLET_NOT_EMPTY = (
        "Wallet still holds a balance away from its zero point — move it out before closing"
    )
    WALLET_CLOSED = "Wallet is closed and cannot take new transactions"
    GOAL_NOT_EMPTY = "Goal still holds money — move it out with a transfer chain before closing"
    GOAL_CLOSED = "Goal is closed and cannot take new transactions"
    CHAIN_CYCLE = "Chain entries reference each other in a cycle"
    IMMUTABLE_CURRENCY = "Wallet currency is fixed at creation and cannot be replaced"
    IMMUTABLE_GOAL_CURRENCY = "Goal currency is fixed at creation and cannot be replaced"
