"""Cache-key builders used by the write-side eviction/version effects.

The read path builds the same keys; pinning the format here guards against a
silent divergence that would orphan cache entries.
"""

from data_read_core.query_slices.get_webhook.infra import (
    get_single_cache_key as get_read_single_webhook_key,
)
from data_read_core.query_slices.list_webhook_events.infra import (
    get_events_cache_key as get_read_webhook_events_key,
)
from data_read_core.query_slices.list_webhooks.infra import (
    get_list_version_key as get_read_webhook_list_version_key,
)
from data_read_core.write_reactions._cache_keys import (
    get_single_transaction_key,
    get_single_wallet_key,
    get_single_webhook_key,
    get_transaction_list_version_key,
    get_wallet_list_version_key,
    get_webhook_events_key,
    get_webhook_list_version_key,
)


def test_single_wallet_key():
    assert get_single_wallet_key("w1") == "read:wallet:w1"


def test_single_transaction_key():
    assert get_single_transaction_key("t1") == "read:transaction:t1"


def test_wallet_list_version_key_is_per_user():
    assert get_wallet_list_version_key(7) == "ver:wallets:7"


def test_transaction_list_version_key_is_per_user():
    assert get_transaction_list_version_key(7) == "ver:transactions:7"


def test_wallet_and_transaction_namespaces_are_disjoint():
    assert get_wallet_list_version_key(7) != get_transaction_list_version_key(7)
    assert get_single_wallet_key("x") != get_single_transaction_key("x")


def test_single_webhook_key():
    assert get_single_webhook_key("wh1") == "read:webhook:wh1"


def test_webhook_list_version_key_is_per_user():
    assert get_webhook_list_version_key(7) == "ver:webhooks:7"


def test_webhook_events_key():
    assert get_webhook_events_key("wh1") == "read:webhook_events:wh1"


def test_webhook_write_keys_match_read_side_keys():
    assert get_single_webhook_key("wh1") == get_read_single_webhook_key("wh1")
    assert get_webhook_list_version_key(7) == get_read_webhook_list_version_key(7)
    assert get_webhook_events_key("wh1") == get_read_webhook_events_key("wh1")
