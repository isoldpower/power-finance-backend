from data_read_core.query_slices.list_transactions.infra import (
    get_list_cache_key as transaction_list_cache_key,
)
from data_read_core.query_slices.list_transactions.infra import (
    get_list_version_key as transaction_list_version_key,
)
from data_read_core.query_slices.list_wallets.infra import (
    get_filter_hash as wallet_filter_hash,
)
from data_read_core.query_slices.list_wallets.infra import (
    get_list_cache_key as wallet_list_cache_key,
)
from data_read_core.query_slices.list_wallets.infra import (
    get_list_version_key as wallet_list_version_key,
)


def test_filter_hash_is_key_order_independent():
    a = wallet_filter_hash({"currency": "USD", "credit": True})
    b = wallet_filter_hash({"credit": True, "currency": "USD"})

    assert a == b


def test_filter_hash_distinguishes_different_filters():
    assert wallet_filter_hash({}) != wallet_filter_hash({"currency": "USD"})


def test_filter_hash_empty_dict_is_stable():
    assert wallet_filter_hash({}) == "bf21a9e8fbc5a384"


def test_wallet_and_transaction_namespaces_are_disjoint():
    assert wallet_list_version_key(7) == "ver:wallets:7"
    assert transaction_list_version_key(7) == "ver:transactions:7"

    wallet_key = wallet_list_cache_key(7, 0, "deadbeef", 20, "first")
    transaction_key = transaction_list_cache_key(7, 0, "deadbeef", 20, "first")
    assert wallet_key.startswith("read:wallets:")
    assert transaction_key.startswith("read:transactions:")
    assert wallet_key != transaction_key


def test_cache_key_embeds_version_filter_and_page():
    key = wallet_list_cache_key(
        user_id=7,
        version=3,
        filter_hash="abc123",
        limit=10,
        cursor="Y3Vyc29y",
    )

    assert key == "read:wallets:7:v3:fabc123:l10:cY3Vyc29y"


def test_first_page_and_cursor_page_get_different_keys():
    """The cursor already encodes the anchor, the direction and the query
    fingerprint, so it is the whole cache identity of a page bar its size."""

    first = wallet_list_cache_key(7, 3, "abc123", 10, "first")
    second = wallet_list_cache_key(7, 3, "abc123", 10, "Y3Vyc29y")

    assert first != second
