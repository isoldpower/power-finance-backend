"""Index names and mapping definitions for the ES projections."""

from data_read_core.shared.elasticsearch import (
    INDEX_DEFINITIONS,
    TRANSACTIONS_INDEX,
    TRANSACTIONS_MAPPING,
    WALLETS_INDEX,
    WALLETS_MAPPING,
)
from data_read_core.shared.elasticsearch.defined_mappings.shared_config import (
    MONEY_SCALING_FACTOR,
)


def test_index_names():
    assert TRANSACTIONS_INDEX == "read_transactions"
    assert WALLETS_INDEX == "read_wallets"


def test_index_definitions_pair_each_index_with_its_mapping():
    assert INDEX_DEFINITIONS == {
        WALLETS_INDEX: WALLETS_MAPPING,
        TRANSACTIONS_INDEX: TRANSACTIONS_MAPPING,
    }


def test_money_scaling_factor_matches_two_decimal_places():
    assert MONEY_SCALING_FACTOR == 100


def test_transaction_amount_is_scaled_float():
    amount = TRANSACTIONS_MAPPING["mappings"]["properties"]["amount"]
    assert amount == {"type": "scaled_float", "scaling_factor": MONEY_SCALING_FACTOR}


def test_wallet_balance_is_scaled_float_and_title_is_full_text():
    properties = WALLETS_MAPPING["mappings"]["properties"]
    assert properties["balance"]["type"] == "scaled_float"
    assert properties["title"]["type"] == "text"
    assert properties["title"]["fields"]["keyword"]["type"] == "keyword"
