"""The conventions themselves, across every endpoint of every service.

Written against the generated OpenAPI documents rather than per endpoint, which
is the point: an endpoint added tomorrow is covered without this file changing,
and that is what stops the surface drifting one endpoint at a time.
"""

import pytest

from ..schema_walk import (
    all_success_bodies,
    collection_metas,
    is_nullable,
    properties_of,
    public_operations,
    type_of,
    walk_properties,
)

ENVELOPE_KEYS = {"data", "meta"}
ERROR_KEYS = {"error", "meta"}
PAGE_META_KEYS = {"limit", "total", "next_cursor", "prev_cursor"}

# Timestamps are `<verb>_at` throughout. `next_attempt_at`, `last_run_at`,
# `acknowledged_at` and the rest all follow it.
TIMESTAMP_SUFFIX = "_at"

# Names that end in `_at` and are NOT timestamps.
NOT_A_TIMESTAMP = frozenset({"applied_at"})

MONEY_KEYS = {"amount", "currency"}


def _identify(item) -> str:
    return str(item[0])


def test_the_documents_publish_a_surface_to_check():
    assert len(public_operations()) > 30
    assert len(all_success_bodies()) > 30


@pytest.mark.parametrize("case", all_success_bodies(), ids=_identify)
def test_every_success_is_the_data_meta_envelope(case):
    """Two exceptions exist in the target and neither is a JSON body: the SSE
    stream and the chat socket. Everything with a JSON response is enveloped."""

    operation, status, body = case
    keys = set(properties_of(operation.document, body))

    assert (
        keys == ENVELOPE_KEYS
    ), f"{operation} answers {status} with {sorted(keys)}, not a data/meta envelope"


@pytest.mark.parametrize("case", all_success_bodies(), ids=_identify)
def test_both_envelope_halves_are_required(case):
    """`meta` is `{}` when there is nothing to say, never absent — a client
    should not have to check whether the key exists."""

    operation, _, body = case
    required = set(body.get("required", ()))

    if not required:
        pytest.skip(f"{operation} publishes no required list")

    assert required >= ENVELOPE_KEYS


@pytest.mark.parametrize("operation", public_operations(), ids=str)
def test_every_operation_documents_a_failure(operation):
    """An operation that declares only a 200 tells a generated client that it
    cannot fail, which is never true — authentication alone can refuse it."""

    assert operation.failure_statuses, f"{operation} documents no error response"


@pytest.mark.parametrize("operation", public_operations(), ids=str)
def test_every_failure_is_the_error_envelope(operation):
    for status in operation.failure_statuses:
        body = operation.body_of(status)
        if body is None:
            continue

        keys = set(properties_of(operation.document, body))
        assert (
            keys == ERROR_KEYS
        ), f"{operation} answers {status} with {sorted(keys)}, not an error envelope"


@pytest.mark.parametrize("operation", public_operations(), ids=str)
def test_an_error_body_names_a_code_and_a_message(operation):
    for status in operation.failure_statuses:
        body = operation.body_of(status)
        if body is None:
            continue

        error = properties_of(operation.document, body).get("error", {})
        fields = set(properties_of(operation.document, error))

        assert {
            "code",
            "message",
        } <= fields, f"{operation} answers {status} with an error body of {sorted(fields)}"


@pytest.mark.parametrize("case", collection_metas(), ids=_identify)
def test_every_collection_carries_the_page_meta(case):
    """Including the non-paginated ones: they report `limit: null` and null
    cursors rather than omitting the keys, so one client code path reads both."""

    operation, meta = case
    keys = set(properties_of(operation.document, meta))

    assert keys >= PAGE_META_KEYS, f"{operation} returns a collection whose meta is {sorted(keys)}"


@pytest.mark.parametrize("case", collection_metas(), ids=_identify)
def test_a_cursor_is_an_opaque_nullable_string(case):
    """Opaque means a string. A client that could parse one would come to
    depend on what is inside it."""

    operation, meta = case
    properties = properties_of(operation.document, meta)

    for cursor in ("next_cursor", "prev_cursor"):
        definition = properties[cursor]
        assert type_of(definition) == {"string"}, f"{operation}: {cursor} is not a string"
        assert is_nullable(definition), f"{operation}: {cursor} cannot be null"


@pytest.mark.parametrize("case", all_success_bodies(), ids=_identify)
def test_money_is_never_a_json_number(case):
    """The rule the whole money grammar rests on: an amount is a decimal string
    at the currency's own scale. A float would reintroduce the rounding error
    the shape exists to prevent."""

    operation, _, body = case

    for name, definition in walk_properties(operation.document, body):
        fields = set(properties_of(operation.document, definition))
        if not fields >= MONEY_KEYS:
            continue

        amount = properties_of(operation.document, definition)["amount"]
        assert type_of(amount) == {
            "string"
        }, f"{operation}: money at {name!r} declares amount as {type_of(amount)}"


@pytest.mark.parametrize("case", all_success_bodies(), ids=_identify)
def test_every_timestamp_is_an_iso_string(case):
    operation, _, body = case

    for name, definition in walk_properties(operation.document, body):
        if not name.endswith(TIMESTAMP_SUFFIX) or name in NOT_A_TIMESTAMP:
            continue
        if type_of(definition) == {"object"} or "properties" in definition:
            continue

        assert type_of(definition) == {
            "string"
        }, f"{operation}: {name!r} is {type_of(definition)}, not an ISO-8601 string"
