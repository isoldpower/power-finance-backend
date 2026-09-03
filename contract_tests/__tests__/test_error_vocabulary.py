"""The two closed error vocabularies, held against the target's tables.

A code the services can emit that the document does not list is a surprise for
every client. A status the services attach to a documented code that disagrees
with the table is worse: the client's retry logic reads the status.
"""

import pytest

from ..documents import diff_document
from ..vocabularies import service_codes, target_detail_codes, target_error_codes

SERVICES = tuple(service_codes())

# Codes the implementation raises that the target's table does not list. Each is
# additive and is written down in API_DIFF.md; a fourth appearing here without
# a line there is a client learning about it from a 500-page log.
EXTRA_ERROR_CODES = frozenset({"service_unavailable", "insufficient_funds", "conflict"})

# The target's Detail Codes table has no generic member for "this field is the
# wrong shape", so one was added.
EXTRA_DETAIL_CODES = frozenset({"invalid"})


def test_both_target_tables_were_found():
    assert len(target_error_codes()) > 20
    assert len(target_detail_codes()) > 15


@pytest.mark.parametrize("service", SERVICES)
def test_no_undocumented_error_code_can_be_raised(service):
    raised = set(service_codes()[service]["error"])
    surprises = raised - set(target_error_codes()) - EXTRA_ERROR_CODES

    assert not surprises, (
        f"{service} can raise {sorted(surprises)}, which is in neither "
        "API_TARGET.md's table nor the documented extras"
    )


@pytest.mark.parametrize("service", SERVICES)
def test_no_undocumented_detail_code_can_be_raised(service):
    raised = set(service_codes()[service]["detail"])
    surprises = raised - target_detail_codes() - EXTRA_DETAIL_CODES

    assert not surprises, f"{service} can raise detail codes {sorted(surprises)}"


@pytest.mark.parametrize("service", SERVICES)
def test_every_code_carries_the_status_the_target_gives_it(service):
    """The status is what a client's retry logic reads. A `rate_limited` served
    as 400 would be retried never, and a `conflict` served as 500 forever."""

    documented = target_error_codes()

    for code, status in service_codes()[service]["error"].items():
        if code not in documented:
            continue

        assert (
            status == documented[code]
        ), f"{service} serves {code!r} as {status}, the target says {documented[code]}"


@pytest.mark.parametrize("code", sorted(EXTRA_ERROR_CODES | EXTRA_DETAIL_CODES))
def test_every_extra_code_is_explained_to_clients(code):
    assert (
        f"`{code}`" in diff_document()
    ), f"{code!r} is raised, is not in API_TARGET.md, and API_DIFF.md does not mention it"


@pytest.mark.parametrize("code", sorted(EXTRA_ERROR_CODES))
def test_every_extra_error_code_is_actually_raised_somewhere(code):
    """Stops this list rotting the other way: an entry for a code nothing can
    raise would hide a later regression."""

    assert any(code in service_codes()[service]["error"] for service in SERVICES)


def test_the_django_services_agree_on_the_whole_vocabulary():
    """They keep separate copies — the house pattern — so nothing but a test
    stops one growing a code the other has never heard of."""

    read = service_codes()["read-service"]
    write = service_codes()["write-service"]

    assert read["error"] == write["error"]
    assert set(read["detail"]) == set(write["detail"])


def test_the_staleness_status_is_not_in_the_client_vocabulary():
    """507 is internal, between read-service and the gateway. It has no
    `error.code`, and giving it one would invite clients to handle it."""

    assert 507 not in set(target_error_codes().values())
    for service in SERVICES:
        assert 507 not in set(service_codes()[service]["error"].values())
