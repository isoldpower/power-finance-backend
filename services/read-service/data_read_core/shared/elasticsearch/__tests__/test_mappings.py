from data_read_core.shared.elasticsearch import (
    AUTOMATIONS_INDEX,
    AUTOMATIONS_MAPPING,
    GOALS_INDEX,
    GOALS_MAPPING,
    INDEX_DEFINITIONS,
    TRANSACTIONS_INDEX,
    TRANSACTIONS_MAPPING,
    WALLETS_INDEX,
    WALLETS_MAPPING,
)
from data_read_core.shared.elasticsearch.defined_mappings.shared_config import (
    MONEY_SCALING_FACTOR,
    SINGLE_NODE_REPLICA_COUNT,
)


def test_index_names():
    assert TRANSACTIONS_INDEX == "read_transactions"
    assert WALLETS_INDEX == "read_wallets"
    assert AUTOMATIONS_INDEX == "read_automations"
    assert GOALS_INDEX == "read_goals"


def test_index_definitions_pair_each_index_with_its_mapping():
    assert INDEX_DEFINITIONS == {
        WALLETS_INDEX: WALLETS_MAPPING,
        TRANSACTIONS_INDEX: TRANSACTIONS_MAPPING,
        AUTOMATIONS_INDEX: AUTOMATIONS_MAPPING,
        GOALS_INDEX: GOALS_MAPPING,
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


def test_goal_money_is_scaled_float_and_title_is_full_text():
    properties = GOALS_MAPPING["mappings"]["properties"]
    assert properties["target"]["type"] == "scaled_float"
    assert properties["progress"]["type"] == "scaled_float"
    assert properties["title"]["fields"]["keyword"]["type"] == "keyword"


def test_automation_rule_body_is_stored_but_never_indexed():
    properties = AUTOMATIONS_MAPPING["mappings"]["properties"]
    assert properties["filter_body"] == {"type": "object", "enabled": False}
    assert properties["effects"] == {"type": "object", "enabled": False}


def test_no_index_asks_for_a_replica_a_single_node_cannot_allocate():
    assert SINGLE_NODE_REPLICA_COUNT == 0

    for definition in INDEX_DEFINITIONS.values():
        assert definition["settings"]["number_of_replicas"] == SINGLE_NODE_REPLICA_COUNT
