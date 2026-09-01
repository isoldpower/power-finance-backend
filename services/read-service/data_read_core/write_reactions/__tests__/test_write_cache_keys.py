from data_read_core.query_slices.get_account.infra import (
    get_single_cache_key as get_read_single_account_key,
)
from data_read_core.query_slices.get_webhook.infra import (
    get_single_cache_key as get_read_single_webhook_key,
)
from data_read_core.query_slices.list_accounts.infra import (
    get_list_version_key as get_read_account_list_version_key,
)
from data_read_core.query_slices.list_webhook_events.infra import (
    get_events_cache_key as get_read_webhook_events_key,
)
from data_read_core.query_slices.list_webhooks.infra import (
    get_list_version_key as get_read_webhook_list_version_key,
)
from data_read_core.shared.metrics import (
    get_account_version_key as get_metrics_account_version_key,
)
from data_read_core.shared.metrics import (
    get_transaction_version_key as get_metrics_transaction_version_key,
)
from data_read_core.write_reactions._cache_keys import (
    get_account_list_version_key,
    get_single_account_key,
    get_single_transaction_key,
    get_single_wallet_key,
    get_single_webhook_key,
    get_transaction_list_version_key,
    get_wallet_list_version_key,
    get_webhook_events_key,
    get_webhook_list_version_key,
)


def test_single_wallet_key():
    assert get_single_wallet_key("w1") == "read:wallet:s2:w1"


def test_single_transaction_key():
    assert get_single_transaction_key("t1") == "read:transaction:s2:t1"


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


def test_account_list_version_key_is_per_user():
    assert get_account_list_version_key(7) == "ver:accounts:7"


def test_single_account_key_is_per_account():
    assert get_single_account_key("a1") == "read:account:s1:a1"


def test_account_write_keys_match_read_side_keys():
    """The bump and the lookup are written in two different slices. If they
    ever disagree the cache silently stops invalidating — pages keep serving a
    ledger that has already moved."""

    assert get_account_list_version_key(7) == get_read_account_list_version_key(7)
    assert get_single_account_key("a1") == get_read_single_account_key("a1")


def test_account_namespaces_do_not_collide_with_wallets_or_transactions():
    assert get_account_list_version_key(7) != get_wallet_list_version_key(7)
    assert get_account_list_version_key(7) != get_transaction_list_version_key(7)


def test_metrics_read_the_same_version_counters_the_reactions_bump():
    """Metrics invent no counter of their own — they compose the transaction and
    account ones. If those spellings drift, every metric silently serves a
    number the ledger has already moved past."""

    assert get_metrics_transaction_version_key(7) == get_transaction_list_version_key(7)
    assert get_metrics_account_version_key(7) == get_account_list_version_key(7)
