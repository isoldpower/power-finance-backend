"""Domain failures become contract errors at the HTTP boundary.

The domain stays free of status codes and the views stay free of `except`
ladders; the mapping lives in one place and is asserted here.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.core.exceptions import ObjectDoesNotExist

from data_write_core.application.exceptions import FallbackTransactionNotVisibleError
from data_write_core.domain import exceptions as domain
from data_write_core.presentation.http.exception_handler import write_exception_handler

WALLET_ID = uuid4()


def render(exc: Exception):
    return write_exception_handler(exc, {"request": None})


@pytest.mark.parametrize(
    "exc",
    [
        ObjectDoesNotExist(),
        domain.WebhookNotFoundError(WALLET_ID),
        domain.NotificationNotFoundError(WALLET_ID),
        domain.TransactionDoesNotBelongToWalletError(uuid4(), WALLET_ID),
        FallbackTransactionNotVisibleError("ledger effect"),
    ],
)
def test_missing_or_foreign_resources_are_404_not_403(exc):
    """403 would confirm the id exists and turn every UUID path in the API into
    an existence oracle."""

    response = render(exc)

    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


def test_a_cancelled_transaction_reads_as_already_deleted():
    response = render(domain.TransactionAlreadyCancelledError(uuid4()))

    assert response.status_code == 404
    assert response.data["error"]["code"] == "already_deleted"


def test_duplicate_subscription_is_a_conflict():
    response = render(domain.DuplicateWebhookSubscriptionError(WALLET_ID, "transaction.created"))

    assert response.status_code == 409
    assert response.data["error"]["code"] == "subscription_exists"


def test_unsupported_currency_is_unprocessable():
    response = render(domain.UnsupportedCurrencyError("XYZ"))

    assert response.status_code == 422
    assert response.data["error"]["code"] == "unsupported_currency"


def test_amount_precision_names_the_field_and_the_reason():
    response = render(domain.AmountPrecisionError(Decimal("50.005"), "USD", 2))

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_failed"
    assert response.data["error"]["details"] == [
        {
            "field": "amount",
            "code": "amount_precision",
            "message": "USD allows 2 fraction digits",
        }
    ]


def test_an_immutable_currency_is_a_field_failure_not_a_server_error():
    response = render(domain.WalletCurrencyImmutableError("USD", "EUR"))

    assert response.status_code == 422
    assert response.data["error"]["details"][0]["field"] == "currency"


def test_unmapped_failures_stay_500_and_leak_nothing():
    response = render(RuntimeError("postgres://user:hunter2@db"))

    assert response.status_code == 500
    assert response.data["error"]["code"] == "internal_error"
    assert "hunter2" not in response.data["error"]["message"]
    assert "details" not in response.data["error"]
