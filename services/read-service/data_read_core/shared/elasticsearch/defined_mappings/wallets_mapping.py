from .shared_config import MONEY_SCALING_FACTOR

WALLETS_INDEX = "read_wallets"

WALLETS_MAPPING: dict = {
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
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
        },
    },
}
