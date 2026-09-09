from .shared_config import MONEY_SCALING_FACTOR, SINGLE_NODE_REPLICA_COUNT

WALLETS_INDEX = "read_wallets"

WALLETS_MAPPING: dict = {
    "settings": {"number_of_replicas": SINGLE_NODE_REPLICA_COUNT},
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "user_id": {"type": "long"},
            "title": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 256},
                },
            },
            "currency_code": {"type": "keyword"},
            "balance": {"type": "scaled_float", "scaling_factor": MONEY_SCALING_FACTOR},
            "zero_balance": {"type": "scaled_float", "scaling_factor": MONEY_SCALING_FACTOR},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "deleted_at": {"type": "date"},
            "category": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 256},
                },
            },
            "color": {"type": "keyword"},
            "favorite": {"type": "boolean"},
        },
    },
}
