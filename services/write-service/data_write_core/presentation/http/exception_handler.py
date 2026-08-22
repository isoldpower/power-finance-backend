from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from write_service.common.http_contract import (
    ApiError,
    Conflict,
    DetailCode,
    ErrorCode,
    ErrorDetail,
    NotFound,
    ValidationFailed,
    api_exception_handler,
)

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
)

UNPROCESSABLE_STATES = (
    domain.TransactionDirectionChangeError,
    domain.ConflictingMoneyFlowDataError,
    domain.TransactionAlreadyAdjustedError,
    domain.CannotCancelInverseTransactionError,
    domain.CannotAdjustAdjustmentTransactionError,
)

AMOUNT_FIELD = "amount"
CURRENCY_FIELD = "currency"
EVENT_TYPE_FIELD = "event_type"

ALREADY_CANCELLED_MESSAGE = "Transaction has already been cancelled"
DUPLICATE_SUBSCRIPTION_MESSAGE = "Webhook already subscribes to that event"
INSUFFICIENT_FUNDS_MESSAGE = "Wallet does not hold enough funds for this transaction"
WALLET_NOT_EMPTY_MESSAGE = (
    "Wallet still holds a balance away from its zero point — move it out before closing"
)
WALLET_CLOSED_MESSAGE = "Wallet is closed and cannot take new transactions"
CHAIN_CYCLE_MESSAGE = "Chain entries reference each other in a cycle"

CHAIN_ENTRY_FIELD = "transactions[{index}].after"
IMMUTABLE_CURRENCY_MESSAGE = "Wallet currency is fixed at creation and cannot be replaced"


def write_exception_handler(exception: Exception, context: dict[str, Any]) -> Response:
    return api_exception_handler(translate(exception), context)


def translate(exception: Exception) -> Exception:
    try:
        raise exception
    except ApiError:
        return exception
    except MISSING_RESOURCES:
        return NotFound()
    except domain.TransactionAlreadyCancelledError:
        return NotFound(ALREADY_CANCELLED_MESSAGE, code=ErrorCode.ALREADY_DELETED)
    except domain.DuplicateWebhookSubscriptionError:
        return Conflict(DUPLICATE_SUBSCRIPTION_MESSAGE, code=ErrorCode.SUBSCRIPTION_EXISTS)
    except domain.InsufficientFundsError:
        return Conflict(INSUFFICIENT_FUNDS_MESSAGE, code=ErrorCode.INSUFFICIENT_FUNDS)
    except domain.WalletNotEmptyError:
        return Conflict(WALLET_NOT_EMPTY_MESSAGE, code=ErrorCode.WALLET_NOT_EMPTY)
    except domain.WalletClosedError:
        return Conflict(WALLET_CLOSED_MESSAGE, code=ErrorCode.WALLET_CLOSED)
    except domain.TransactionChainCycleError:
        return ValidationFailed(CHAIN_CYCLE_MESSAGE, code=ErrorCode.CHAIN_CYCLE)
    except domain.TransactionChainTooLongError as error:
        return ValidationFailed(str(error), code=ErrorCode.CHAIN_TOO_LONG)
    except domain.TransactionChainUnknownReferenceError as error:
        return ValidationFailed(
            str(error),
            code=ErrorCode.CHAIN_UNKNOWN_REFERENCE,
            details=[
                ErrorDetail(
                    field=CHAIN_ENTRY_FIELD.format(index=error.index),
                    code=DetailCode.NOT_A_REFERENCE,
                    message=str(error),
                )
            ],
        )
    except domain.UnsupportedCurrencyError as error:
        return ValidationFailed(
            f"Currency {error.currency_code!r} is not supported",
            code=ErrorCode.UNSUPPORTED_CURRENCY,
        )
    except Exception:
        return _translate_field_failure(exception)


def _translate_field_failure(exception: Exception) -> Exception:
    try:
        raise exception
    except domain.AmountPrecisionError as error:
        return _field_error(
            AMOUNT_FIELD,
            DetailCode.AMOUNT_PRECISION,
            f"{error.currency_code} allows {error.decimals} fraction digits",
        )
    except (domain.NegativeMoneyError, domain.InvalidTransactionAmountError) as error:
        return _field_error(AMOUNT_FIELD, DetailCode.OUT_OF_BOUNDS, str(error))
    except domain.CurrencyMismatchError as error:
        return _field_error(CURRENCY_FIELD, DetailCode.CURRENCY_MISMATCH, str(error))
    except domain.WalletCurrencyImmutableError:
        return _field_error(CURRENCY_FIELD, DetailCode.INVALID, IMMUTABLE_CURRENCY_MESSAGE)
    except domain.UnsupportedWebhookEventTypeError as error:
        return _field_error(EVENT_TYPE_FIELD, DetailCode.UNKNOWN_EVENT_TYPE, str(error))
    except UNPROCESSABLE_STATES as error:
        return ValidationFailed(str(error))
    except Exception:
        return exception


def _field_error(field: str, code: DetailCode, message: str) -> ValidationFailed:
    return ValidationFailed(details=[ErrorDetail(field=field, code=code, message=message)])
