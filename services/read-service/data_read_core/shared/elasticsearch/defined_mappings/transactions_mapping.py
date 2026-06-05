from .shared_config import MONEY_SCALING_FACTOR

TRANSACTIONS_INDEX = "read_transactions"

TRANSACTIONS_MAPPING: dict = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "wallet_id": {"type": "keyword"},
            "user_id": {"type": "long"},
            "amount": {"type": "scaled_float", "scaling_factor": MONEY_SCALING_FACTOR},
            "currency_code": {"type": "keyword"},
            "occurred_at": {"type": "date"},
            "created_at": {"type": "date"},
        },
    },
}
