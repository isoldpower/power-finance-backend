from .shared_config import MONEY_SCALING_FACTOR, SINGLE_NODE_REPLICA_COUNT

GOALS_INDEX = "read_goals"

GOALS_MAPPING: dict = {
    "settings": {"number_of_replicas": SINGLE_NODE_REPLICA_COUNT},
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "user_id": {"type": "long"},
            "title": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "currency_code": {"type": "keyword"},
            "target": {"type": "scaled_float", "scaling_factor": MONEY_SCALING_FACTOR},
            "progress": {"type": "scaled_float", "scaling_factor": MONEY_SCALING_FACTOR},
            "url": {"type": "keyword"},
            "finish_at": {"type": "date"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "deleted_at": {"type": "date"},
        },
    },
}
