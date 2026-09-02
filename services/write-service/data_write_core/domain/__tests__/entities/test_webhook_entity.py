from datetime import datetime, timedelta

from data_write_core.domain.entities import WebhookEntity
from data_write_core.domain.entities.webhook import SECRET_GRACE_PERIOD

MOMENT = datetime(2026, 8, 12, 11, 51)


def make_webhook() -> WebhookEntity:
    return WebhookEntity(
        id="11111111-1111-1111-1111-111111111111",
        title="Ledger sync",
        url="https://hooks.example.com/finance/ledger",
        secret="whsec_first",
        user_id="7",
        created_at=MOMENT,
        updated_at=MOMENT,
    )


def test_a_new_endpoint_has_one_secret_and_no_grace_window():
    webhook = make_webhook()

    assert webhook.secret_version == 1
    assert webhook.previous_secret == ""
    assert webhook.previous_secret_expires_at is None


def test_rotation_keeps_the_replaced_secret_for_the_grace_period():
    webhook = make_webhook()

    rotation = webhook.rotate_secret(now=MOMENT)

    assert rotation.secret != "whsec_first"
    assert webhook.secret == rotation.secret
    assert webhook.previous_secret == "whsec_first"
    assert webhook.previous_secret_version == 1
    assert webhook.secret_version == 2
    assert webhook.previous_secret_expires_at == MOMENT + SECRET_GRACE_PERIOD


def test_rotating_twice_inside_the_window_drops_the_oldest_secret():
    """Only two secrets are ever live. A third rotation invalidates the oldest
    immediately rather than widening the window."""

    webhook = make_webhook()
    webhook.rotate_secret(now=MOMENT)
    second_secret = webhook.secret

    webhook.rotate_secret(now=MOMENT + timedelta(hours=1))

    assert webhook.previous_secret == second_secret
    assert "whsec_first" not in (webhook.secret, webhook.previous_secret)
    assert webhook.secret_version == 3
    assert webhook.previous_secret_version == 2


def test_restoring_a_snapshot_undoes_the_whole_rotation():
    """A failed saga must not leave a new secret beside a stale grace window."""

    webhook = make_webhook()
    before = webhook.secret_snapshot()
    webhook.rotate_secret(now=MOMENT)

    webhook.restore_secret(before, now=MOMENT)

    assert webhook.secret == "whsec_first"
    assert webhook.secret_version == 1
    assert webhook.previous_secret == ""
    assert webhook.previous_secret_version is None
    assert webhook.previous_secret_expires_at is None


def test_enabled_is_the_pause_switch_and_survives_a_partial_update():
    webhook = make_webhook()

    webhook.update(now=MOMENT, enabled=False)
    assert not webhook.enabled
    assert webhook.title == "Ledger sync"

    webhook.update(now=MOMENT, title="Renamed")
    assert not webhook.enabled
    assert webhook.title == "Renamed"


def test_changing_the_url_does_not_rotate_the_secret():
    """The same secret now signs requests to a different host, which is the
    user's decision to make."""

    webhook = make_webhook()

    webhook.update(now=MOMENT, url="https://elsewhere.example.com/hook")

    assert webhook.secret == "whsec_first"
    assert webhook.secret_version == 1
