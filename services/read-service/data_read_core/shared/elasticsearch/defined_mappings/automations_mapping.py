from .shared_config import SINGLE_NODE_REPLICA_COUNT

AUTOMATIONS_INDEX = "read_automations"

AUTOMATIONS_MAPPING: dict = {
    "settings": {"number_of_replicas": SINGLE_NODE_REPLICA_COUNT},
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "user_id": {"type": "long"},
            "name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "icon": {"type": "keyword"},
            "enabled": {"type": "boolean"},
            "trigger_type": {"type": "keyword"},
            "trigger_event": {"type": "keyword"},
            "trigger_schedule": {"type": "keyword"},
            "filter_body": {"type": "object", "enabled": False},
            "effects": {"type": "object", "enabled": False},
            "runs": {"type": "integer"},
            "last_run_at": {"type": "date"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "deleted_at": {"type": "date"},
        },
    },
}
