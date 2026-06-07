"""Cache-key builders used by the write-side eviction/version effects.

The read path builds the same keys; pinning the format here guards against a
silent divergence that would orphan cache entries.
"""

from data_read_core.write_reactions._cache_keys import (
    get_single_transaction_key,
    get_single_wallet_key,
    get_transaction_list_version_key,
    get_wallet_list_version_key,
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
