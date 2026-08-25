from typing import Any

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

from data_write_core.domain import exceptions as domain

from ._exception_messages import (
    FIELDS,
    MESSAGES,
    MISSING_RESOURCES,
    UNPROCESSABLE_STATES,
)


def write_exception_handler(exception: Exception, context: dict[str, Any]) -> Response:
    return api_exception_handler(
        translate(exception),
        context,
    )


def translate(exception: Exception) -> Exception:
    try:
        raise exception
    except ApiError:
        return exception
    except MISSING_RESOURCES:
        return NotFound()
    except domain.TransactionAlreadyCancelledError:
        return NotFound(MESSAGES.ALREADY_CANCELLED, code=ErrorCode.ALREADY_DELETED)
    except domain.DuplicateWebhookSubscriptionError:
        return Conflict(MESSAGES.DUPLICATE_SUBSCRIPTION, code=ErrorCode.SUBSCRIPTION_EXISTS)
    except domain.InsufficientFundsError:
        return Conflict(MESSAGES.INSUFFICIENT_FUNDS, code=ErrorCode.INSUFFICIENT_FUNDS)
    except domain.WalletNotEmptyError:
        return Conflict(MESSAGES.WALLET_NOT_EMPTY, code=ErrorCode.WALLET_NOT_EMPTY)
    except domain.WalletClosedError:
        return Conflict(MESSAGES.WALLET_CLOSED, code=ErrorCode.WALLET_CLOSED)
    except domain.GoalNotEmptyError:
        return Conflict(MESSAGES.GOAL_NOT_EMPTY, code=ErrorCode.GOAL_NOT_EMPTY)
    except domain.GoalClosedError:
        return Conflict(
            MESSAGES.GOAL_CLOSED,
            code=ErrorCode.WALLET_CLOSED,
        )
    except domain.TransactionChainCycleError:
        return ValidationFailed(
            MESSAGES.CHAIN_CYCLE,
            code=ErrorCode.CHAIN_CYCLE,
        )
    except domain.TransactionChainTooLongError as error:
        return ValidationFailed(str(error), code=ErrorCode.CHAIN_TOO_LONG)
    except domain.TransactionChainUnknownReferenceError as error:
        return ValidationFailed(
            str(error),
            code=ErrorCode.CHAIN_UNKNOWN_REFERENCE,
            details=[
                ErrorDetail(
                    field=FIELDS.CHAIN_ENTRY.format(index=error.index),
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
            FIELDS.AMOUNT,
            DetailCode.AMOUNT_PRECISION,
            f"{error.currency_code} allows {error.decimals} fraction digits",
        )
    except (domain.NegativeMoneyError, domain.InvalidTransactionAmountError) as error:
        return _field_error(FIELDS.AMOUNT, DetailCode.OUT_OF_BOUNDS, str(error))
    except domain.CurrencyMismatchError as error:
        return _field_error(FIELDS.CURRENCY, DetailCode.CURRENCY_MISMATCH, str(error))
    except domain.WalletCurrencyImmutableError:
        return _field_error(FIELDS.CURRENCY, DetailCode.INVALID, MESSAGES.IMMUTABLE_CURRENCY)
    except domain.GoalCurrencyImmutableError:
        return _field_error(FIELDS.CURRENCY, DetailCode.INVALID, MESSAGES.IMMUTABLE_GOAL_CURRENCY)
    except domain.UnsupportedWebhookEventTypeError as error:
        return _field_error(FIELDS.EVENT_TYPE, DetailCode.UNKNOWN_EVENT_TYPE, str(error))
    except UNPROCESSABLE_STATES as error:
        return ValidationFailed(str(error))
    except Exception:
        return exception


def _field_error(field: str, code: DetailCode, message: str) -> ValidationFailed:
    return ValidationFailed(
        details=[
            ErrorDetail(
                field=field,
                code=code,
                message=message,
            )
        ]
    )
