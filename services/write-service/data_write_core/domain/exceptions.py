from decimal import Decimal
from uuid import UUID


class DomainError(Exception):
    pass


class UnsupportedCurrencyError(DomainError):
    def __init__(self, currency_code: str) -> None:
        self.currency_code = currency_code

        super().__init__(f"Unsupported currency code '{currency_code}'.")


class WebhookNotFoundError(DomainError):
    def __init__(self, webhook_id: UUID) -> None:
        self.webhook_id = webhook_id

        super().__init__(f"Webhook with ID {webhook_id} not found.")


class WebhookSubscriptionNotFoundError(DomainError):
    def __init__(self, subscription_id: UUID) -> None:
        self.subscription_id = subscription_id

        super().__init__(f"Webhook subscription with ID {subscription_id} not found.")


class UnsupportedWebhookEventTypeError(DomainError):
    def __init__(self, event_type: str) -> None:
        self.event_type = event_type

        super().__init__(f"Unsupported webhook event type '{event_type}'.")


class DuplicateWebhookSubscriptionError(DomainError):
    def __init__(self, webhook_id: UUID, event_type: str) -> None:
        self.webhook_id = webhook_id
        self.event_type = event_type

        super().__init__(f"Webhook {webhook_id} is already subscribed to '{event_type}'.")


class NotificationNotFoundError(DomainError):
    def __init__(self, notification_id: UUID) -> None:
        self.notification_id = notification_id

        super().__init__(f"Notification with ID {notification_id} not found.")


class WalletCurrencyImmutableError(DomainError):
    def __init__(self, current_currency: str, requested_currency: str) -> None:
        self.current_currency = current_currency
        self.requested_currency = requested_currency

        super().__init__(
            f"Wallet currency is immutable: wallet is denominated in {current_currency}, "
            f"cannot replace with {requested_currency}."
        )


class WalletNotEmptyError(DomainError):
    def __init__(self, balance: Decimal, zero_balance: Decimal) -> None:
        self.balance = balance
        self.zero_balance = zero_balance

        super().__init__(
            f"Wallet is not empty: balance {balance} differs from its zero point {zero_balance}."
        )


class CurrencyMismatchError(DomainError):
    def __init__(self, from_currency: str, to_currency: str) -> None:
        self.from_currency = from_currency
        self.to_currency = to_currency

        super().__init__(f"Currency code mismatch: expected {from_currency} but got {to_currency}.")


class InsufficientFundsError(DomainError):
    def __init__(self, amount: Decimal, available: Decimal) -> None:
        self.amount = amount
        self.available = available

        super().__init__(f"Insufficient funds: requested {amount}, available {available}.")


class AmountPrecisionError(DomainError):
    def __init__(self, amount: Decimal, currency_code: str, decimals: int) -> None:
        self.amount = amount
        self.currency_code = currency_code
        self.decimals = decimals

        super().__init__(f"{currency_code} allows {decimals} fraction digits, got {amount}.")


class NegativeMoneyError(DomainError):
    def __init__(self, amount: Decimal) -> None:
        self.amount = amount

        super().__init__(f"Money amount must be non-negative, got {amount}.")


class EventCollectorClosedError(DomainError):
    def __init__(self) -> None:
        super().__init__("Cannot collect events from a closed collector.")


class InvalidTransactionAmountError(DomainError):
    def __init__(self, amount: Decimal) -> None:
        self.amount = amount

        super().__init__(f"Transaction amount must be non-zero, got {amount}.")


class TransactionDoesNotBelongToWalletError(DomainError):
    def __init__(self, transaction_id: UUID, wallet_id: UUID) -> None:
        self.transaction_id = transaction_id
        self.wallet_id = wallet_id

        super().__init__(f"Transaction {transaction_id} does not belong to wallet {wallet_id}.")


class TransactionDirectionChangeError(DomainError):
    def __init__(self, transaction_id: UUID, current_type: str, requested_type: str) -> None:
        self.transaction_id = transaction_id
        self.current_type = current_type
        self.requested_type = requested_type

        super().__init__(
            f"Transaction {transaction_id} is an {current_type} and cannot be adjusted "
            f"into an {requested_type}."
        )


class TransactionChainCycleError(DomainError):
    def __init__(self) -> None:
        super().__init__("Chain entries form a cycle through their `after` references.")


class TransactionChainUnknownReferenceError(DomainError):
    def __init__(self, index: int, reference: str) -> None:
        self.index = index
        self.reference = reference

        super().__init__(f"Chain entry {index} references unknown temporary id {reference!r}.")


class TransactionChainTooLongError(DomainError):
    def __init__(self, length: int, maximum: int) -> None:
        self.length = length
        self.maximum = maximum

        super().__init__(f"A chain carries at most {maximum} entries, got {length}.")


class TransactionChainNotFoundError(DomainError):
    def __init__(self, chain_id: UUID) -> None:
        self.chain_id = chain_id

        super().__init__(f"Transaction chain {chain_id} not found.")


class WalletClosedError(DomainError):
    def __init__(self, wallet_id: UUID) -> None:
        self.wallet_id = wallet_id

        super().__init__(f"Wallet {wallet_id} is closed and cannot take new transactions.")


class TransactionAlreadyCancelledError(DomainError):
    def __init__(self, transaction_id: UUID) -> None:
        self.transaction_id = transaction_id

        super().__init__(f"Transaction {transaction_id} has already been cancelled.")


class ConflictingMoneyFlowDataError(DomainError):
    def __init__(self) -> None:
        super().__init__("Transaction cannot both cancel and adjust another transaction.")


class TransactionAlreadyAdjustedError(DomainError):
    def __init__(self, transaction_id: UUID) -> None:
        self.transaction_id = transaction_id

        super().__init__(f"Transaction {transaction_id} has already been adjusted.")


class CannotCancelInverseTransactionError(DomainError):
    def __init__(self, transaction_id: UUID) -> None:
        self.transaction_id = transaction_id

        super().__init__(
            f"Transaction {transaction_id} is itself an inverse and cannot be cancelled."
        )


class CannotAdjustAdjustmentTransactionError(DomainError):
    def __init__(self, transaction_id: UUID) -> None:
        self.transaction_id = transaction_id

        super().__init__(
            f"Transaction {transaction_id} is itself an adjustment and cannot be adjusted."
        )


class GoalNotEmptyError(DomainError):
    def __init__(self, progress: Decimal) -> None:
        self.progress = progress

        super().__init__(f"Goal is not empty: it still holds {progress}.")


class GoalClosedError(DomainError):
    def __init__(self, goal_id: UUID) -> None:
        self.goal_id = goal_id

        super().__init__(f"Goal {goal_id} is closed and cannot take new transactions.")


class GoalCurrencyImmutableError(DomainError):
    def __init__(self, current_currency: str, requested_currency: str) -> None:
        self.current_currency = current_currency
        self.requested_currency = requested_currency

        super().__init__(
            f"Goal currency is immutable: goal is denominated in {current_currency}, "
            f"cannot replace with {requested_currency}."
        )


class MoneyContainerNotFoundError(DomainError):
    def __init__(self, container_id: UUID) -> None:
        self.container_id = container_id

        super().__init__(f"No wallet or goal with ID {container_id}.")


class ActionNotFoundError(DomainError):
    def __init__(self, action_id: UUID) -> None:
        self.action_id = action_id

        super().__init__(f"Action with ID {action_id} not found.")


class ActionAlreadyResolvedError(DomainError):
    def __init__(self, action_id: UUID) -> None:
        self.action_id = action_id

        super().__init__(f"Action with ID {action_id} has already been answered.")


class UnknownResolutionError(DomainError):
    def __init__(self, resolution_id: str) -> None:
        self.resolution_id = resolution_id

        super().__init__(f"Resolution {resolution_id!r} is not offered by this action.")
