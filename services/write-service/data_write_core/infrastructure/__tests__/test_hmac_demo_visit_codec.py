import re
from datetime import UTC, datetime, timedelta

import pytest

from data_write_core.infrastructure.demo import HmacDemoVisitCodec

DEMO_SESSION_SECRET = "a-demo-session-secret-of-at-least-32-characters"
GATEWAY_TEST_VECTOR = "dv1_q8n3V0kz5tX2bYp1mW7cRg_1vuhmo0_5kLPnLI9aV1kvR4cILOTig"
GATEWAY_TEST_VECTOR_EXPIRY = datetime.fromtimestamp(4102444800, UTC)
LEGACY_DEMO_SESSION_SHAPE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def _codec_at(moment: datetime, secret: str = DEMO_SESSION_SECRET) -> HmacDemoVisitCodec:
    return HmacDemoVisitCodec(
        secret=secret,
        lifetime=timedelta(hours=24),
        clock=lambda: moment,
    )


def _replace_character(text: str, position: int, replacement: str) -> str:
    return text[:position] + replacement + text[position + 1 :]


def test_an_issued_visit_fits_the_gateway_identifier_shape():
    issued_visit = _codec_at(datetime.now(UTC)).issue()

    assert LEGACY_DEMO_SESSION_SHAPE.fullmatch(issued_visit.identifier)
    assert issued_visit.identifier.startswith("dv1_")
    assert issued_visit.nonce in issued_visit.identifier


def test_an_issued_visit_expires_after_the_lifetime():
    issued_at = datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC)

    issued_visit = _codec_at(issued_at).issue()

    assert issued_visit.expires_at == issued_at + timedelta(hours=24)


def test_every_issued_visit_has_its_own_nonce():
    codec = _codec_at(datetime.now(UTC))

    assert codec.issue().nonce != codec.issue().nonce


def test_an_issued_visit_verifies_until_it_expires():
    issued_at = datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC)
    issued_visit = _codec_at(issued_at).issue()

    verified_visit = _codec_at(issued_at + timedelta(hours=23)).verify(issued_visit.identifier)

    assert verified_visit == issued_visit
    assert _codec_at(issued_at + timedelta(hours=24)).verify(issued_visit.identifier) is None


def test_the_gateway_test_vector_verifies():
    verified_visit = _codec_at(GATEWAY_TEST_VECTOR_EXPIRY - timedelta(seconds=1)).verify(
        GATEWAY_TEST_VECTOR
    )

    assert verified_visit is not None
    assert verified_visit.nonce == "q8n3V0kz5tX2bYp1mW7cRg"
    assert verified_visit.expires_at == GATEWAY_TEST_VECTOR_EXPIRY


@pytest.mark.parametrize(
    "tampered_identifier",
    [
        _replace_character(GATEWAY_TEST_VECTOR, 4, "Z"),
        GATEWAY_TEST_VECTOR.replace("_1vuhmo0_", "_2vuhmo0_"),
        _replace_character(GATEWAY_TEST_VECTOR, len(GATEWAY_TEST_VECTOR) - 1, "A"),
        "dv2" + GATEWAY_TEST_VECTOR[3:],
        GATEWAY_TEST_VECTOR.replace("_1vuhmo0_", "_1VUHMO0_"),
        "f3b1c2d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
        "",
    ],
)
def test_a_tampered_or_foreign_identifier_is_rejected(tampered_identifier):
    codec = _codec_at(GATEWAY_TEST_VECTOR_EXPIRY - timedelta(seconds=1))

    assert codec.verify(tampered_identifier) is None


def test_another_secret_rejects_the_identifier():
    codec = _codec_at(
        GATEWAY_TEST_VECTOR_EXPIRY - timedelta(seconds=1),
        secret=DEMO_SESSION_SECRET + "x",
    )

    assert codec.verify(GATEWAY_TEST_VECTOR) is None
