from .shared_config import MONEY_SCALING_FACTOR

TRANSACTIONS_INDEX = "read_transactions"

TRANSACTIONS_MAPPING: dict = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "wallet_id": {"type": "keyword"},
            "wallet_name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "user_id": {"type": "long"},
            "amount": {"type": "scaled_float", "scaling_factor": MONEY_SCALING_FACTOR},
            "currency_code": {"type": "keyword"},
            "name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "category": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "evidence_url": {"type": "keyword"},
            "origin": {"type": "keyword"},
            "type": {"type": "keyword"},
            "chain_id": {"type": "keyword"},
            "chain_sort": {"type": "keyword"},
            "occurred_at": {"type": "date"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "deleted_at": {"type": "date"},
        },
    },
}
