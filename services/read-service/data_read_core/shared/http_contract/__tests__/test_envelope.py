import pytest
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework import serializers

from data_read_core.shared.http_contract import (
    DetailCode,
    ErrorCode,
    ErrorDetail,
    NotFound,
    ValidationFailed,
    api_exception_handler,
    error_payload,
    ok,
)


def render(exc: Exception):
    return api_exception_handler(exc, {"request": None})


def test_success_envelope_has_exactly_data_and_meta():
    response = ok({"id": "w1"}, {"cached": True})

    assert set(response.data) == {"data", "meta"}
    assert response.data["data"] == {"id": "w1"}
    assert response.data["meta"] == {"cached": True}


def test_meta_is_an_empty_object_rather_than_null_when_there_is_nothing_to_report():
    assert ok({"id": "w1"}).data["meta"] == {}


def test_error_envelope_carries_code_message_and_request_id():
    payload = error_payload(ErrorCode.NOT_FOUND, "Resource does not exist")

    assert set(payload) == {"error", "meta"}
    assert payload["error"]["code"] == "not_found"
    assert "details" not in payload["error"]
    assert set(payload["meta"]) == {"request_id", "timestamp"}


def test_details_are_present_only_for_field_level_failures():
    payload = error_payload(
        ErrorCode.VALIDATION_FAILED,
        "Request body failed validation",
        [ErrorDetail("amount", DetailCode.AMOUNT_PRECISION, "USD allows 2 fraction digits")],
    )

    assert payload["error"]["details"] == [
        {"field": "amount", "code": "amount_precision", "message": "USD allows 2 fraction digits"}
    ]


def test_api_errors_render_with_their_own_status():
    response = render(NotFound())

    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


def test_validation_failures_are_422_with_details():
    response = render(
        ValidationFailed(
            details=[ErrorDetail("amount", DetailCode.AMOUNT_MALFORMED, "not a decimal")]
        )
    )

    assert response.status_code == 422
    assert response.data["error"]["details"][0]["code"] == "amount_malformed"


def test_serializer_failures_become_validation_failed_with_field_paths():
    class Body(serializers.Serializer):
        amount = serializers.CharField()

    serializer = Body(data={})
    serializer.is_valid()

    response = render(drf_exceptions.ValidationError(serializer.errors))

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_failed"
    assert response.data["error"]["details"][0]["field"] == "amount"
    assert response.data["error"]["details"][0]["code"] == "required"


def test_nested_serializer_failures_report_a_json_path():
    detail = {"effects": [{}, {"type": [drf_exceptions.ErrorDetail("bad", code="invalid")]}]}

    response = render(drf_exceptions.ValidationError(detail))

    assert response.data["error"]["details"][0]["field"] == "effects[1].type"


def test_missing_resources_are_not_found():
    assert render(Http404()).status_code == 404


def test_unhandled_failures_are_500_with_no_detail_and_no_exception_text(caplog):
    """An exception string in a response body is an information leak as much as
    a contract violation."""

    response = render(RuntimeError("connection string: postgres://user:hunter2@db"))

    assert response.status_code == 500
    assert response.data["error"]["code"] == "internal_error"
    assert "details" not in response.data["error"]
    assert "hunter2" not in response.data["error"]["message"]


@pytest.mark.parametrize(
    ("exc", "expected_status", "expected_code"),
    [
        (drf_exceptions.NotAuthenticated(), 401, "unauthorized"),
        (drf_exceptions.AuthenticationFailed(), 401, "unauthorized"),
        (drf_exceptions.PermissionDenied(), 403, "forbidden"),
        (drf_exceptions.Throttled(), 429, "rate_limited"),
    ],
)
def test_framework_failures_map_onto_contract_codes(exc, expected_status, expected_code):
    response = render(exc)

    assert response.status_code == expected_status
    assert response.data["error"]["code"] == expected_code


def test_read_at_least_507_keeps_its_status_for_the_gateway():
    """The gateway's read-fallback plugin keys on 507 to re-issue the read
    against the write side; a client never sees it."""

    from data_read_core.shared.read_at_least import ReadModelNotCaughtUp

    response = render(ReadModelNotCaughtUp())

    assert response.status_code == 507
    assert set(response.data) == {"error", "meta"}
